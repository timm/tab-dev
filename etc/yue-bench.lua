-- bench.lua: how long does it cost to import tab.yue?
-- usage: lua5.5 bench.lua /abs/path/tab.yue /abs/path/tab.lua [reps]
local yuePath = arg[1]
local luaPath = arg[2]
local reps    = tonumber(arg[3]) or 50

package.cpath = os.getenv("HOME") .. "/.luarocks/lib/lua/5.5/?.so;" .. package.cpath

local function bench(reps, fn)       -- cpu seconds per rep, best of reps
  local best, tot = math.huge, 0
  for _ = 1, reps do
    local t0 = os.clock()
    fn()
    local d = os.clock() - t0
    tot = tot + d
    if d < best then best = d end
  end
  return tot / reps, best
end

-- 1. load the compiler itself
local t0 = os.clock()
local yue = require("yue")
local loadYue = os.clock() - t0

-- 2. read the source
local h = io.open(yuePath); local src = h:read("a"); h:close()
local readMean = bench(reps, function()
  local f = io.open(yuePath); local s = f:read("a"); f:close(); return s
end)

-- 3. transpile
local out, err = yue.to_lua(src, {implicit_return_root = true})
assert(out, err)
local lxMean, lxBest = bench(reps, function()
  local o, e = yue.to_lua(src, {implicit_return_root = true})
  assert(o, e)
end)

-- 4. lua's own parse of the generated code, and of the handwritten file
local hl = io.open(luaPath); local lsrc = hl:read("a"); hl:close()
lsrc = lsrc:gsub("^#[^\n]*", "")     -- load() rejects a shebang; loadfile skips it
local pGenMean = bench(reps, function() assert(load(out)) end)
local pHandMean = bench(reps, function() assert(load(lsrc)) end)

-- 5. execute the chunk (reads help, builds `the`, defines everything)
local runMean = bench(reps, function() assert(load(out))() end)

print(("yue version          %s"):format(yue.version))
print(("source               %d bytes, %d lines"):format(
        #src, select(2, src:gsub("\n", "")) + 1))
print(("generated lua        %d bytes, %d lines"):format(
        #out, select(2, out:gsub("\n", "")) + 1))
print("")
print(("require 'yue' (once) %8.2f ms"):format(loadYue * 1000))
print(("read tab.yue         %8.3f ms"):format(readMean * 1000))
print(("transpile  mean      %8.2f ms   <- the yue tax"):format(lxMean * 1000))
print(("transpile  best      %8.2f ms"):format(lxBest * 1000))
print(("load(generated lua)  %8.2f ms"):format(pGenMean * 1000))
print(("load(tab.lua)        %8.2f ms   baseline"):format(pHandMean * 1000))
print(("load + run generated %8.2f ms"):format(runMean * 1000))
print("")
print(("import tab.yue cold  %8.2f ms  (yue.so + read + transpile + load + run)")
      :format((loadYue + readMean + lxMean + runMean) * 1000))
print(("import tab.yue warm  %8.2f ms  (compiler already loaded)")
      :format((readMean + lxMean + runMean) * 1000))
print(("import tab.lua       %8.2f ms  (read + load + run)")
      :format((readMean + pHandMean + runMean) * 1000))
print(("reps                 %8d"):format(reps))
