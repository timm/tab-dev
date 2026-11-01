# docs/Makefile (tab-dev): tectonic build of the SP&E paper.  Code
# enters via snips/, cut fresh from the sibling ../tab sources on
# every build by tab's own ,/snips tool.
DOC ?= tab
TAB ?= ../../tab

$(DOC).pdf: $(DOC).tex snips
	tectonic $(DOC).tex

.PHONY: snips
snips: $(TAB)/,/snips $(TAB)/tab.lua $(TAB)/tab-eg.lua $(TAB)/tree.lua
	@$(TAB)/,/snips $(CURDIR)/snips

clean:
	rm -rf snips $(DOC).pdf refs.bib

view: $(DOC).pdf ## build, then open
	open $(DOC).pdf
