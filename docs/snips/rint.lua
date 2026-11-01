function rint(n) --> int; an int in 1..`n`, repeatable from `the.seed`.
  the.seed = (16807 * the.seed) % 2147483647
  return 1 + floor(n * the.seed / 2147483647) end
