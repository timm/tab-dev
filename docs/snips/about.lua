function about(    t) --> nil
  print":config"                    -- a section, so a reader (and
  t = {date = os.date"%Y-%m-%d %H:%M:%S", version = the.version,
       cmd  = (arg and arg[0] or "?")
              .. (arg and #arg > 0
                  and " " .. table.concat(arg, " ") or "")}
  print(logfmt(t))
  print(logfmt(the)) end
