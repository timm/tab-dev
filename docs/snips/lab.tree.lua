function lab.tree(    tr,te,y) --> nil
  tr, te, y = halves()
  Tree(tr, tr.rows, y):show() end
