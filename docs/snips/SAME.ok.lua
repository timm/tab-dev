function SAME.ok(i) --> bool; true if all stats pass
  return i:cohen() <= .35 and i:cliffs() <= .195 and i:ks() <= 1.36 end
