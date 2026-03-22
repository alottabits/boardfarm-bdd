-- Format log output as [timestamp] [container_name] message
-- Extracts container name from Docker config.v2.json (cached for performance)

local container_name_cache = {}

local function get_container_name(container_id)
    if container_name_cache[container_id] then
        return container_name_cache[container_id]
    end
    local config_path = "/var/lib/docker/containers/" .. container_id .. "/config.v2.json"
    local f = io.open(config_path, "r")
    if not f then
        container_name_cache[container_id] = container_id:sub(1, 12)
        return container_name_cache[container_id]
    end
    local content = f:read("*a")
    f:close()
    -- Name in config.v2.json: "Name":"/container_name" or "Name":"container_name"
    local name = content:match('"Name":"/?([^"]+)"')
    if name then
        name = name:gsub("^/", "")
    else
        name = container_id:sub(1, 12)
    end
    container_name_cache[container_id] = name
    return name
end

function format_log(tag, timestamp, record)
    local filepath = record["filepath"]
    if not filepath then
        record["container_name"] = "unknown"
    else
        local container_id = filepath:match("/containers/([^/]+)/")
        if container_id then
            record["container_name"] = get_container_name(container_id)
        else
            record["container_name"] = "unknown"
        end
    end
    local time_str = record["time"] or "unknown"
    local container = record["container_name"] or "unknown"
    local log_msg = record["log"] or ""
    log_msg = log_msg:gsub("\n$", "")
    record["formatted"] = string.format("[%s] [%s] %s", time_str, container, log_msg)
    record["log"] = record["formatted"]
    return 2, timestamp, record
end
