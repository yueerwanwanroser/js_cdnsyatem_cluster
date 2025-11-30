-- APISIX CDN 防御插件
-- 集成到网关层的防御逻辑

local http = require("resty.http")
local cjson = require("cjson")
local redis = require("resty.redis")

local schema = {
    type = "object",
    properties = {
        defense_engine_url = {
            type = "string",
            description = "防御引擎 URL"
        },
        redis_host = {
            type = "string",
            description = "Redis 主机"
        },
        redis_port = {
            type = "integer",
            description = "Redis 端口"
        },
        tenant_id = {
            type = "string",
            description = "租户 ID"
        },
        enable_js_challenge = {
            type = "boolean",
            description = "启用 JS 验证"
        }
    },
    required = {"defense_engine_url", "tenant_id"}
}

local plugin_name = "cdn-defense"

local _M = {
    version = "0.1.0",
    priority = 2000,  -- 高优先级
    type = "auth",
    schema = schema
}

-- 连接到防御引擎
local function connect_defense_engine()
    local httpc = http.new()
    return httpc
end

-- 连接到 Redis
local function connect_redis(redis_host, redis_port)
    local red = redis:new()
    local ok, err = red:connect(redis_host or "127.0.0.1", redis_port or 6379)
    if not ok then
        ngx.log(ngx.ERR, "无法连接到 Redis: " .. err)
        return nil
    end
    return red
end

-- 提取请求信息
local function extract_request_info()
    return {
        request_id = ngx.var.request_id or ngx.md5(ngx.var.remote_addr .. ngx.now()),
        timestamp = ngx.now(),
        client_ip = ngx.var.remote_addr,
        user_agent = ngx.var.http_user_agent or "",
        path = ngx.var.uri,
        method = ngx.var.request_method,
        headers = ngx.req.get_headers(),
        payload_size = tonumber(ngx.var.content_length or 0),
        x_forwarded_for = ngx.var.http_x_forwarded_for or ""
    }
end

-- 调用防御引擎
local function call_defense_engine(defense_engine_url, request_info, tenant_id)
    local httpc = http.new()
    
    local body = cjson.encode({
        request = request_info,
        tenant_id = tenant_id,
        timestamp = ngx.now()
    })
    
    local res, err = httpc:request_uri(
        defense_engine_url .. "/analyze",
        {
            method = "POST",
            headers = {
                ["Content-Type"] = "application/json"
            },
            body = body,
            timeout = 1000
        }
    )
    
    if not res then
        ngx.log(ngx.ERR, "防御引擎请求失败: " .. (err or "未知错误"))
        -- 失败时允许请求通过
        return nil
    end
    
    if res.status ~= 200 then
        ngx.log(ngx.ERR, "防御引擎返回错误: " .. res.status)
        return nil
    end
    
    local decision = cjson.decode(res.body)
    return decision
end

-- 生成 JS 挑战页面
local function generate_js_challenge(request_id, tenant_id)
    local challenge_html = [[
<!DOCTYPE html>
<html>
<head>
    <title>安全验证</title>
    <style>
        body { font-family: Arial; text-align: center; padding-top: 100px; }
        .container { background: #f5f5f5; padding: 30px; border-radius: 5px; max-width: 400px; margin: 0 auto; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>安全验证进行中</h1>
        <p>请稍候...</p>
        <div class="spinner"></div>
    </div>
    <script>
        // 生成指纹
        function getFingerprint() {
            return {
                ua: navigator.userAgent,
                lang: navigator.language,
                platform: navigator.platform,
                cores: navigator.hardwareConcurrency || 'unknown',
                screen: window.screen.width + 'x' + window.screen.height,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                time: Date.now()
            };
        }
        
        // 验证浏览器功能
        function verifyBrowser() {
            if (!navigator.userAgent) return false;
            if (typeof Array.from !== 'function') return false;
            if (typeof Promise !== 'function') return false;
            return true;
        }
        
        // 计算挑战响应
        function computeChallenge() {
            if (!verifyBrowser()) {
                console.log('浏览器验证失败');
                return null;
            }
            
            var fp = getFingerprint();
            var challenge = {
                request_id: ']] .. request_id .. [[',
                fingerprint: fp,
                timestamp: Date.now(),
                tenant_id: ']] .. tenant_id .. [['
            };
            
            return btoa(JSON.stringify(challenge));
        }
        
        // 提交验证
        function submitChallenge() {
            var response = computeChallenge();
            if (!response) {
                window.location.reload();
                return;
            }
            
            fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'X-JS-Challenge-Response': response,
                    'X-Request-ID': ']] .. request_id .. [['
                }
            }).then(function(resp) {
                if (resp.ok) {
                    window.location.reload();
                }
            });
        }
        
        // 自动提交
        window.onload = function() {
            setTimeout(submitChallenge, 1000);
        };
    </script>
</body>
</html>
    ]]
    
    return challenge_html
end

-- 检查 JS 挑战响应
local function verify_js_challenge(response_header, request_id)
    if not response_header then
        return false
    end
    
    -- 解码 Base64
    local decoded = ngx.decode_base64(response_header)
    if not decoded then
        return false
    end
    
    local challenge_data = cjson.decode(decoded)
    if not challenge_data then
        return false
    end
    
    -- 验证请求 ID
    if challenge_data.request_id ~= request_id then
        return false
    end
    
    -- 验证浏览器指纹
    if not challenge_data.fingerprint or not challenge_data.fingerprint.ua then
        return false
    end
    
    return true
end

-- 缓存防御结果
local function cache_decision(red, cache_key, decision, ttl)
    if not red then
        return
    end
    
    red:setex(cache_key, ttl or 60, cjson.encode(decision))
end

-- 获取缓存的防御结果
local function get_cached_decision(red, cache_key)
    if not red then
        return nil
    end
    
    local cached = red:get(cache_key)
    if cached then
        return cjson.decode(cached)
    end
    return nil
end

-- 访问阶段
function _M.access(conf)
    ngx.log(ngx.NOTICE, "CDN 防御插件处理请求")
    
    -- 提取请求信息
    local request_info = extract_request_info()
    
    -- 连接 Redis
    local red = connect_redis(conf.redis_host, conf.redis_port)
    
    -- 检查缓存
    local cache_key = "defense:decision:" .. request_info.client_ip .. ":" .. conf.tenant_id
    if red then
        local cached_decision = get_cached_decision(red, cache_key)
        if cached_decision then
            ngx.log(ngx.NOTICE, "使用缓存的防御结果")
            if not cached_decision.allow then
                ngx.status = 403
                ngx.say(cjson.encode({error = cached_decision.reason}))
                return
            end
        end
    end
    
    -- 检查 JS 挑战响应
    if ngx.var.request_method == "POST" then
        local js_response = ngx.var.http_x_js_challenge_response
        if js_response then
            local request_id = ngx.var.http_x_request_id or request_info.request_id
            if verify_js_challenge(js_response, request_id) then
                ngx.log(ngx.NOTICE, "JS 验证通过")
                
                -- 缓存通过结果
                if red then
                    local pass_decision = {
                        allow = true,
                        threat_score = 0,
                        action = "allow"
                    }
                    cache_decision(red, cache_key, pass_decision, 300)
                end
                return
            else
                ngx.log(ngx.WARN, "JS 验证失败")
            end
        end
    end
    
    -- 调用防御引擎
    local decision = call_defense_engine(
        conf.defense_engine_url,
        request_info,
        conf.tenant_id
    )
    
    if not decision then
        ngx.log(ngx.WARN, "防御引擎不可用，允许请求通过")
        return
    end
    
    -- 缓存决策
    if red then
        cache_decision(red, cache_key, decision, 60)
    end
    
    -- 根据决策响应
    if decision.action == "block" then
        ngx.status = 403
        ngx.say(cjson.encode({
            error = decision.reason,
            threat_score = decision.threat_score
        }))
        return
    end
    
    if decision.action == "rate_limit" then
        ngx.status = 429
        ngx.say(cjson.encode({
            error = "请求过于频繁",
            retry_after = decision.block_duration
        }))
        return
    end
    
    if decision.require_js_challenge and conf.enable_js_challenge then
        ngx.status = 200
        ngx.say(generate_js_challenge(request_info.request_id, conf.tenant_id))
        ngx.exit(200)
        return
    end
    
    ngx.log(ngx.NOTICE, "请求通过: " .. decision.reason)
end

return _M
