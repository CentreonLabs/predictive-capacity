--
-- Copyright 2020-2023 Centreon
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--
-- For more information : contact@centreon.com
--
-- This is a streamconnector to send data on the Centreon data lake.
-- To use it, you have to configure a streamconnector broker output
-- with several parameters:
--
-- filters_files (array of strings given in configuration by a file names
-- separated by a comma): This is an array of json files. These
-- files are used to select hosts, services, metrics to send to the data lake.
-- Two formats are supported, here is an example of the first one:
--         {
--           "filters": {
--             "197": {
--               "2701": {
--                 "connection":1
--               },
--               "2708": {
--                 "traffic_in":1
--               }
--             },
--             "198": {
--               "2651": {
--                 "conpsec":1
--               }
--             }
--           }
--         }
--     where "197" and "198" are host_id, "2701", "2708" and "2651" are
--     service_id and "connection", "traffic_in", "conpsec" are metrics.
--
-- Here is an example of the second format:
-- {
--   "schema": {
--     "version": "1.0.0",
--     "name": "centreon-collector"
--   },
--   "services": [
--     {
--       "host_id": 12,
--       "service_id": 23,
--       "status": false,
--       "downtime": false
--     }
--   ],
--   "metrics": [
--     {
--       "host_id": 23,
--       "service_id": 23,
--       "name": "used",
--       "bounds": ["min", "critical_low"]
--     }
--   ],
--   "hosts": [
--     {
--       "host_id": 12,
--       "status": true,
--       "downtime": false
--     }
--   ],
--   "category": [
--     {
--       "category_id": 5,
--       "status": false,
--       "service_status": false,
--       "host_status": false
--     }
--   ],
--   "metaservices": [],
--   "ba": [
--     {
--       "ba_id": 44,
--       "ba_status": false,
--       "kpi_status": false
--     }
--   ]
-- }
-- This second format is more flexible since it allows to send services, hosts
-- but also metrics, downtimes, etc...
-- This is a work in progress. At the moment we don't do anything with
-- categories, nor with metaservices.
--
-- By default, this array contains only one file that is:
--           /etc/centreon-broker/anomaly-detection-filters.json
--
-- logfile (string): It is this script log file. You have to provide a full
--                   path to the file.
--                   Default value: /var/log/centreon-broker/anomaly-detection.log
-- log_level (number) : The log level filter apply in logfile. This is usually used for debugging.
--                      Default value : 0 (set higher for more log details)
-- destination (string): It is the domain name of the destination
--                   Default value: int.mycentreon.net
-- source: A string to represent this Central
-- proxy (string): The proxy configuration. No value is given by default.
-- max_queue_size (number): The queue max size before data to be sent.
-- token (string): The token to access the platform.
--
local cURL = require "cURL"

local function dump(o, indent)
    if not indent then
        indent = 0
    end
    if type(o) == 'table' then
        local s = '{\n'
        indent = indent + 2
        for k, v in pairs(o) do
            if type(k) ~= 'number' then
                k = '"' .. k .. '"'
            end
            s = s .. string.rep(' ', indent) .. '[' .. k .. '] = ' .. dump(v, indent)
        end
        indent = indent - 2
        return s .. string.rep(' ', indent) .. '}\n'
    else
        return tostring(o) .. '\n'
    end
end

local data = {
    logfile = "/var/log/centreon-broker/anomaly-detection.log",
    log_level = 0,
    filters_files = {"/etc/centreon-broker/filters.json"},
    destination = "prod.mycentreon.com",
    source = "centreon_onprem",
    proxy = "",
    max_queue_size = 10,
    queue = {},
    filter = {}
}

-- the date when the filters files have been loaded
local filters_files_load_date = {}
for i, v in ipairs(data.filters_files) do
    filters_files_load_date[i] = 0
end

-- the last modification date of the file
local filters_files_check_date = 0

-- last time data were sent
local last_time_data_send = 0

local function validate_v2(dec)
    if type(dec) ~= 'table' then
        return false, "filters file should be a json file with a first level object just containing a 'filters' entry."
    end

    if not dec.schema then
        return false, "filters file with new format must contain a schema block with a version and a name."
    end

    for k, v in pairs(dec) do
        if k == "schema" then
            if type(v) ~= 'table' then
                return false, "'schema' entry must be an object."
            end
            for kk, vv in pairs(v) do
                if kk == "version" then
                    if vv ~= "1.0.0" then
                        return false, "Only '1.0.0' is recognized as value of 'schema.version'."
                    end
                elseif kk == "name" then
                    if vv ~= "centreon-collector" then
                        return false, "Only 'centreon-collector' is recognized as value of 'schema.name'."
                    end
                else
                    return false, "The item 'schema." .. kk .. "' is not recognized in filters files."
                end
            end
        elseif k == "hosts" then
            if type(v) ~= 'table' or #v == 0 then
                return false, "'hosts' entry must be an array of objects."
            end
            for kk, vv in ipairs(v) do
                for kkk, vvv in pairs(vv) do
                    if kkk == "host_id" then
                        if type(vvv) ~= "number" or vvv ~= math.floor(vvv) then
                            return false, "The item 'hosts[" .. kk .. "].host_id must be an integer."
                        end
                    elseif kkk == "status" then
                        if type(vvv) ~= "boolean" then
                            return false, "The item 'hosts[" .. kk .. "].status must be an boolean."
                        end
                    elseif kkk == "downtime" then
                        if type(vvv) ~= "boolean" then
                            return false, "The item 'hosts[" .. kk .. "].downtime must be a boolean."
                        end
                    else
                        return false, "The item 'hosts[" .. kk .. "]." .. kkk .. "' is not recognized in filters files."
                    end
                end
            end
        elseif k == "services" or k == "metaservices" then
            if type(v) ~= 'table' or #v == 0 then
                return false, "'" .. k .. "' entry must be an array of objects."
            end
            for kk, vv in ipairs(v) do
                for kkk, vvv in pairs(vv) do
                    if kkk == "host_id" then
                        if type(vvv) ~= "number" or vvv ~= math.floor(vvv) then
                            return false, "The item '" .. k .. "[" .. kk .. "].host_id must be an integer."
                        end
                    elseif kkk == "service_id" then
                        if type(vvv) ~= "number" or vvv ~= math.floor(vvv) then
                            return false, "The item '" .. k .. "[" .. kk .. "].service_id must be an integer."
                        end
                    elseif kkk == "status" then
                        if type(vvv) ~= "boolean" then
                            return false, "The item '" .. k .. "[" .. kk .. "].status' should be a boolean."
                        end
                    elseif kkk == "downtime" then
                        if type(vvv) ~= "boolean" then
                            return false, "The item '" .. k .. "[" .. kk .. "].downtime' should be a boolean."
                        end
                    else
                        return false,
                            "The item '" .. k .. "[" .. kk .. "]." .. kkk .. "' is not recognized in filters files."
                    end
                end
            end
        elseif k == "ba" then
            if type(v) ~= 'table' or #v == 0 then
                return false, "'ba' entry must be an array of objects."
            end
            for kk, vv in ipairs(v) do
                for kkk, vvv in pairs(vv) do
                    if kkk == "ba_id" then
                        if type(vvv) ~= "number" or vvv ~= math.floor(vvv) then
                            return false, "The item 'ba[" .. kk .. "].service_id must be an integer."
                        end
                    elseif kkk == "ba_status" then
                        if type(vvv) ~= "boolean" then
                            return false, "The item 'ba[" .. kk .. "].status' should be a boolean."
                        end
                    else
                        return false, "The item 'ba[" .. kk .. "]." .. kkk .. "' is not recognized in filters files."
                    end
                end
            end
        elseif k == "metrics" then
            if type(v) ~= 'table' then
                return false, "'metrics' entry must be an object."
            end
            for kk, vv in ipairs(v) do
                for kkk, vvv in pairs(vv) do
                    if kkk == "host_id" then
                        if type(vvv) ~= "number" or vvv ~= math.floor(vvv) then
                            return false, "The item 'metrics[" .. kk .. "].host_id must be an integer."
                        end
                    elseif kkk == "service_id" then
                        if type(vvv) ~= "number" or vvv ~= math.floor(vvv) then
                            return false, "The item 'metrics[" .. kk .. "].service_id must be an integer."
                        end
                    elseif kkk == "name" then
                        if type(vvv) ~= "string" then
                            return false, "The item 'metrics[" .. kk .. "].name' should be a string."
                        end
                    elseif kkk == "bounds" then
                        if type(vvv) ~= "table" then
                            return false, "The item 'metrics.bounds' should be an array of strings."
                        end
                    else
                        return false, "The item 'metrics." .. kkk .. "' is not recognized in filters files."
                    end
                end
            end
            --    elseif k == "category" then
            --    elseif k == "metaservices" then
            --    elseif k == "ba" then
        else
            return false, "'" .. k .. "' is not recognized as key in filters files."
        end
    end
    return 2
end

local function validate(dec)
    if type(dec) ~= 'table' then
        return false, "filters file should be a json file with a first level object just containing a 'filters' entry."
    end

    local first = next(dec)
    local second = next(dec, first)
    if first ~= "filters" then
        return validate_v2(dec)
    end
    if second ~= nil then
        return false, "filters file first level object must just contain a 'filters' entry."
    end

    local filters = dec.filters
    if type(filters) ~= 'table' then
        return false, "the 'filters' object must be an object whose keys are host_id."
    end

    for h, host in pairs(filters) do
        local host_id = tonumber(h)
        if not host_id then
            return false, "the key '" .. tostring(h) .. "' inside the 'filter' object should be an integer."
        end
        if type(host) ~= "table" then
            return false, "the key '" .. tostring(h) .. "' inside the 'filter' object does not point to an object."
        end

        for s, service in pairs(host) do
            local service_id = tonumber(s)
            if not service_id then
                return false,
                    "the key '" .. tostring(s) .. "' inside the '" .. h .. "' host object should be an integer."
            end
            if type(service) ~= "table" then
                return false, "the keys '" .. h .. "/" .. tostring(s) ..
                    "' representing a service should contain an object whose keys are metrics."
            end

            for m, metric in pairs(service) do
                if type(m) ~= 'string' then
                    return false, "the key '" .. tostring(m) .. "' inside service " .. h .. "/" .. tostring(s) ..
                        " should be a string representing a metric."
                end
                if metric ~= 0 and metric ~= 1 then
                    return false,
                        "the value associated to the metric '" .. m .. "' in service " .. h .. "/" .. tostring(s) ..
                            " must be 1  if you want it or 0."
                end
            end
        end
    end
    return 1
end

local function file_date(file)
    broker_log:info(3, "file stats " .. tostring(file))
    local file_stats = broker.stat(file)
    return file_stats.mtime
end

local function load_filters()
    for i, filename in ipairs(data.filters_files) do
        local file = io.open(filename, "r")
        if not file then
            broker_log:warning(0, "Unable to read the filter file '" .. filename .. "'")
            return
        else
            -- The file will be read and parsed only if
            -- it has been updated since last time read
            local f_date = file_date(filename)
            if not filters_files_load_date[i] or f_date > filters_files_load_date[i] then
                broker_log:info(0, "Parsing file '" .. filename .. "'")
                filters_files_load_date[i] = f_date
                local content = file:read("*a")
                file:close()
                local dec, err = broker.json_decode(content)
                if dec then
                    local status, valerr = validate(dec)
                    if not status then
                        error(valerr)
                    end
                    data.filter.services = {}
                    data.filter.hosts = {}
                    if status == 1 then
                        -- Status is 1 => first version of filter
                        broker_log:info(2, "Parsing legacy filters")
                        local filters = dec.filters
                        for h, host in pairs(filters) do
                            for s, service in pairs(host) do
                                local metrics = {}
                                for m, metric in pairs(service) do
                                    if metric == 1 then
                                        table.insert(metrics, m)
                                    end
                                end
                                local key = tostring(h) .. ":" .. tostring(s)
                                if not data.filter.services[key] then
                                    data.filter.services[key] = {
                                        metrics = {}
                                    }
                                end
                                for m, metric in ipairs(metrics) do
                                    data.filter.services[key].metrics[metric] = {}
                                end
                            end
                        end
                    else
                        -- Status is 2 => second version of filter
                        broker_log:info(2, "Parsing filters")
                        if dec.services then
                            for i, srv in ipairs(dec.services) do
                                local hid, sid = srv.host_id, srv.service_id
                                data.filter.services[tostring(hid) .. ":" .. tostring(sid)] = {
                                    resource_type = "service",
                                    status = srv.status,
                                    downtime = srv.downtime
                                }
                            end
                        end
                        if dec.metaservices then
                            for i, srv in ipairs(dec.metaservices) do
                                local hid, sid = srv.host_id, srv.service_id
                                data.filter.services[tostring(hid) .. ":" .. tostring(sid)] = {
                                    resource_type = "metaservice",
                                    status = srv.status,
                                    downtime = srv.downtime
                                }
                            end
                        end
                        if dec.hosts then
                            for i, hst in ipairs(dec.hosts) do
                                local hid = hst.host_id
                                data.filter.hosts[hid] = {
                                    resource_type = "host",
                                    status = hst.status,
                                    downtime = hst.downtime
                                }
                            end
                        end
                        local met = {}
                        if dec.metrics then
                            for i, m in ipairs(dec.metrics) do
                                local key = tostring(m.host_id) .. ":" .. tostring(m.service_id)
                                if not data.filter.services[key] then
                                    data.filter.services[key] = {
                                        metrics = {}
                                    }
                                else
                                    if not data.filter.services[key].metrics then
                                        data.filter.services[key].metrics = {}
                                    end
                                end
                                data.filter.services[key].metrics[m.name] = {
                                    bounds = m.bounds
                                }
                            end
                        end
                        data.filter.ba = {}
                        local ba = data.filter.ba
                        if dec.ba then
                            for i, b in ipairs(dec.ba) do
                                local bid = b.ba_id
                                ba[bid] = {
                                    resource_type = "ba",
                                    status = b.status,
                                    downtime = b.downtime
                                }
                            end
                        end
                    end
                else
                    broker_log:error(0, err)
                end
            else
                broker_log:info(1, "No change to filters from file '" .. filename .. "'")
                file:close()
            end
        end
    end
end

-- Init function. It is called when the connector is started by Broker.
--
-- @param conf: The configuration given by the user
--
function init(conf)
    -- Checking if a log level is set in conf file (in the other case log level is set at 0)
    if conf.log_level then
        data.log_level = conf.log_level
    end
    broker_log:set_parameters(data.log_level, data.logfile)

    if conf.logfile then
        data.logfile = conf.logfile
        broker_log:info(2, "Setting the log file to " .. tostring(conf.logfile))
    end
    if conf.filters_files then
        data.filters_files = {}
        for s in string.gmatch(conf.filters_files, "([^,]+)") do
            -- We trim the string
            s = s:gsub("^%s*(.-)%s*$", "%1")
            -- We add it to the filters list.
            table.insert(data.filters_files, s)
        end
        broker_log:info(2, "Setting the filters files to " .. tostring(conf.filters_files))
    end
    if conf.destination then
        data.destination = conf.destination
        broker_log:info(2, "Setting the destination to " .. tostring(conf.destination))
    end

    -- A string to represent this Central source
    if conf.source then
        data.source = conf.source
        broker_log:info(2, "Setting the source to " .. tostring(conf.source))
    end

    if conf.proxy then
        data.proxy = conf.proxy
        broker_log:info(2, "Setting the proxy to " .. tostring(conf.proxy))
    end

    if conf.max_queue_size then
        data.max_queue_size = conf.max_queue_size
        broker_log:info(2, "Setting the max queue size to " .. tostring(conf.max_queue_size))
    end

    if conf.token then
        data.token = conf.token
        broker_log:info(2, "Setting the token value to " .. tostring(conf.token))
    end

    if conf.centreon_platform_uuid then
        data.uuid = conf.centreon_platform_uuid
        broker_log:info(2, "Setting the uuid value to " .. tostring(conf.centreon_platform_uuid))
    end

    local now = os.time(os.date("!*t"))
    if now - filters_files_check_date > 60 then
        load_filters()
        filters_files_check_date = now
    end
end

local function flush_data()
    if #data.queue == 0 then
        return true
    end

    local metrics = table.concat(data.queue, "\\n")
    local timestamp = os.date("!%Y-%m-%dT%TZ")

    local url = data.destination .. "/observability"
    local headers = "-H 'X-Warp10-Token: " .. tostring(data.token) .. "'"
    local postfields = "--data-binary \"$(printf '" .. tostring(metrics):gsub("\n", "\\n") .. "')\""

    if data.proxy and data.proxy ~= "" then
        postfields = postfields .. " -x " .. data.proxy
    end

    local command = "curl -X POST " .. headers .. " " .. postfields .. " '" .. url .. "'"

    broker_log:info(2, metrics)
    broker_log:info(2, "url=" .. url)
    broker_log:info(2, "X-Warp10-Token=" .. tostring(data.token))

    local result = os.execute(command)

    -- Capture exit code
    local exit_code = (result == true) and 0 or (result / 256)

    broker_log:info(2, "Exit code: " .. tostring(exit_code))

    if exit_code ~= 0 then
        broker_log:error(0, "Failed to send data to " .. data.destination)
        broker_log:error(0, "HTTP Code: " .. tostring(exit_code))
        return false
    end

    broker_log:info(2, tostring(#data.queue) .. " data sent")
    broker_log:info(2, "Sent data: " .. metrics)
    data.queue = {}
    broker_log:info(3, "Exiting flush_data()")
    return true
end

-- This is not beautiful. I suppose it was written for the SAAS purposes.
-- We are sure that no retention will be made by broker because of this stream
-- connector.
-- However, if the stream connector fails to write to the SAAS, it can increase
-- its memory consumption since the queue is still not emptied.
function flush()
    broker_log:info(3, "flush(): not doing anything")
    return true
end

-- Function to work with service status.
-- Status, downtimes and metrics for services are handled here.
-- The function fills the data.queue, the write() function takes care of
-- emptying it.
-- @param e Here is the event to handle, we already know it is a
--          pb_service_status or a service_status.
function write_service_status(e)
    -- Are we interested by this service?
    -- Let's take a look at metrics, downtime and status...
    if not data.filter.services then
        return
    end
    local metrics, downtime, status, resource_type
    local key = e.host_id .. ":" .. e.service_id
    if data.filter.services[key] then
        resource_type = data.filter.services[key].resource_type
        metrics = data.filter.services[key].metrics
        downtime = data.filter.services[key].downtime
        status = data.filter.services[key].status
    end

    local in_downtime = '0'
    local current_state

    if e.element == 24 then
        if downtime and e.downtime_depth > 0 then
            in_downtime = '1'
        end
        if status then
            current_state = e.current_state
        end
    elseif e.element == 29 then
        if downtime and e.scheduled_downtime_depth > 0 then
            in_downtime = '1'
        end
        if status then
            current_state = e.state
        end
    end

    local labels = "platform_uuid=" .. tostring(data.uuid) .. ",_cmaas=" .. data.source .. ",service_id=" ..
                       e.service_id .. ",host_id=" .. e.host_id
    if resource_type then
        labels = labels .. ",resource_type=" .. resource_type
    end

    local srvdesc = broker_cache:get_service_description(e.host_id, e.service_id)
    if srvdesc then
        labels = labels .. ",service_name=" .. broker.url_encode(srvdesc)
    else
        broker_log:warning(1, "No service description in cache for service (" .. key .. ")")
    end

    local hostname = broker_cache:get_hostname(e.host_id)
    if hostname then
        labels = labels .. ",host_name=" .. broker.url_encode(hostname)
    else
        broker_log:warning(1, "No host name in cache for host " .. e.host_id)
    end

    -- handle metrics
    local perfdata
    if metrics then
        broker_log:info(3, "Service status with (host_id:service_id)=(" .. key .. ") matches filters")
        perfdata = broker.parse_perfdata(e.perfdata, true)

        for mname, metric in pairs(metrics) do
            local uom = perfdata[mname].uom
            if not uom or uom == "" then
                uom = ""
            else
                uom = ",uom=" .. broker.url_encode(uom)
            end
            local metric_query = tostring(e.last_check) .. '000000// ' .. broker.url_encode(mname) .. '{' ..
                                     tostring(labels) .. uom .. '} ' .. tostring(perfdata[mname].value)
            broker_log:info(3, "Query to send: " .. metric_query)
            table.insert(data.queue, metric_query)
            if metric.bounds then
                for i, n in ipairs(metric.bounds) do
                    if perfdata[mname][n] then
                        local v = perfdata[mname][n]
                        if v == v then
                            local query = tostring(e.last_check) .. '000000// ' .. broker.url_encode(mname) .. ':' ..
                                              broker.url_encode(n) .. '{' .. tostring(labels) .. uom .. '} ' .. v
                            broker_log:info(3, "Query to send: " .. query)
                            table.insert(data.queue, query)
                        end
                    end
                end
            end
        end
    end

    -- handle downtime
    if downtime then
        local downtime = e.last_check .. '000000// centreon:downtime{' .. labels .. '} ' .. in_downtime
        broker_log:info(3, "Query to send: " .. downtime)
        table.insert(data.queue, downtime)
    end

    -- handle status
    if status then
        local state = e.last_check .. '000000// centreon:status{' .. labels .. '} ' .. current_state
        broker_log:info(3, "Query to send: " .. state)
        table.insert(data.queue, state)
    end
end

-- Function to work with host status.
-- Status, downtimes for hosts are handled here.
-- The function fills the data.queue, the write() function takes care of
-- emptying it.
-- @param e Here is the event to handle, we already know it is a
--          pb_host_status or a host_status.
function write_host_status(e)
    -- Are we interested by this host?
    -- Let's take a look at downtime and status...
    if not data.filter.hosts then
        return
    end
    local downtime, status, resource_type
    local key = e.host_id
    if data.filter.hosts[key] then
        resource_type = ",resource_type=" .. data.filter.hosts[key].resource_type
        downtime = data.filter.hosts[key].downtime
        status = data.filter.hosts[key].status
    else
        resource_type = ""
    end

    local in_downtime = '0'
    local current_state

    if e.element == 14 then
        if downtime and e.downtime_depth > 0 then
            in_downtime = '1'
        end
        if status then
            current_state = e.current_state
        end
    elseif e.element == 32 then
        if downtime and e.scheduled_downtime_depth > 0 then
            in_downtime = '1'
        end
        if status then
            current_state = e.state
        end
    end

    local labels = "platform_uuid=" .. tostring(data.uuid) .. ",_cmaas=" .. data.source .. ",host_id=" .. e.host_id ..
                       resource_type

    local hostname = broker_cache:get_hostname(e.host_id)
    if hostname then
        labels = labels .. ",host_name=" .. broker.url_encode(hostname)
    else
        broker_log:warning(1, "No host name in cache for host " .. e.host_id)
    end

    -- handle downtime
    if downtime then
        local downtime = e.last_check .. '000000// centreon:downtime{' .. labels .. '} ' .. in_downtime
        broker_log:info(3, "Query to send: " .. downtime)
        table.insert(data.queue, downtime)
    end

    -- handle status
    if status then
        local state = e.last_check .. '000000// centreon:status{' .. labels .. '} ' .. current_state
        broker_log:info(3, "Query to send: " .. state)
        table.insert(data.queue, state)
    end
end

function write(e)
    -- we check filters file every minutes
    local now = os.time(os.date("!*t"))
    if now - filters_files_check_date > 60 then
        load_filters()
        filters_files_check_date = now
    end

    local done = false
    -- We only want service_status events
    -- Case of service_status events
    if e.category == 1 then
        if e.element == 24 or e.element == 29 then
            write_service_status(e)
            done = true
        elseif e.element == 14 or e.element == 32 then
            write_host_status(e)
            done = true
        end
    end
    if not done then
        broker_log:info(3, "element with type " .. e.category .. ":" .. e.element .. " not managed")
        if #data.queue == 0 then
            return true
        end
        return false
    else
        local retval = false
        if #data.queue >= data.max_queue_size or (#data.queue > 0 and now - last_time_data_send > 300) then
            broker_log:info(3,
                "write_service_status(): time to flush data! queue size: " .. #data.queue .. " - queue age: " ..
                    (now - last_time_data_send))
            retval = flush_data()
            broker_log:info(3, "Exited from flush_data()")
            last_time_data_send = now
        end

        broker_log:info(3, "Exiting write_service_status()")
        return retval
    end
end
