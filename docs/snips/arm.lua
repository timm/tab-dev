function arm(who,how,score,what)    -- one cached run of one arm
  return function()
    print(scored(the.file, who,
                 function(tr,te) return score(tr, te, how) end,
                 what)) end end
