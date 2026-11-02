function slow.show(    tr,te,y) --> nil
  tr, te, y = halves()
  about()
  Tree(tr, tr.rows, y):show() end
