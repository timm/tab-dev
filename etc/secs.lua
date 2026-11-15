-- secs.lua: the lua arm of secs.py.  One fit and predict of tab's
-- forest, timed on a WALL clock, as many times as secs.py's budget
-- allows.
--
-- usage: luajit etc/secs.lua f.csv budget maxfits   (TAB=../tab)
--
-- Prints `fit <wall> <cpu>` per completed fit.  Both clocks, because
-- `os.clock` is cpu time and that is what sank rawnum.png: under load
-- it reads low for an arm that waits.  Here the two should agree, and
-- printing both is how a reader checks that they did.
local ffi = require "ffi"
ffi.cdef [[ typedef struct { long tv_sec; long tv_nsec; } secs_ts;
            int clock_gettime(int, secs_ts *); ]]
local ts = ffi.new "secs_ts"
local MONO = ffi.os == "OSX" and 6 or 1      -- CLOCK_MONOTONIC
local function wall()
  ffi.C.clock_gettime(MONO, ts)
  return tonumber(ts.tv_sec) + tonumber(ts.tv_nsec) / 1e9 end

package.path = (os.getenv "TAB" or "../tab") .. "/?.lua;" .. package.path
local tab = require "tab"
local file, budget, maxfits = arg[1], tonumber(arg[2]), tonumber(arg[3])

local tbl = tab.Tab(file)
tab.seed(1234567891 + 1)
local tr, te = tbl:split()
local train = tbl:clone(tr)
local began, last = wall(), 0
for k = 1, maxfits do
  if k > 1 and wall() - began + last > budget then break end
  local w, c = wall(), os.clock()
  local f = tab.Forest(train)
  for _, row in ipairs(te) do f:guess(row) end
  last = wall() - w
  io.write(("fit %.6f %.6f\n"):format(last, os.clock() - c))
  io.flush() end
