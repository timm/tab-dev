function rint(n) --> int; an int in 1..`n`, repeatable from `the.seed`.
  rng = (16807 * (rng or the.seed)) % 2147483647
  return 1 + floor(n * rng / 2147483647) end
