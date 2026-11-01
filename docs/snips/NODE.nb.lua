function NODE.nb(i) --> NB; leaf's own naive Bayes, fitted the first time
  i.model = i.model or Nb(i.sub, i.rows)
  return i.model end
