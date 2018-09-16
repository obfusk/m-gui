SHELL     := bash
PY        ?= python3
ME        := m-gui.py

TOUCH     := README.md debian/copyright

RM_SECTS  := Description Examples Help Configuration
RM_SKIP   := 'minimalistic media manager'

.PHONY: test test_verbose coverage clean cleanup install fix_mtimes \
        package _publish _dch

test:
	$(PY) $(ME) --help        # at least check for syntax errors

test_verbose: test # TODO

coverage:
	false # TODO

clean:
	rm -fr .coverage htmlcov/
	rm -fr README.rst m-gui.1 m-gui.1.md build/ dist/ mmm_gui.egg-info/
	find -name '*.pyc' -delete
	find -name __pycache__ -delete

cleanup: clean
	rm -fr debian/.debhelper debian/debhelper-build-stamp \
	  debian/files debian/mmm-gui/ debian/mmm-gui.debhelper.log \
	  debian/mmm-gui.substvars

# NB: maybe not the best place to call fix_mtimes, but dh_auto_install
# runs before dh_installdocs and we only use the install target for
# dpkg-buildpackage anyway.
install: fix_mtimes m-gui.1
	test -d "$(DESTDIR)"
	mkdir -p "$(DESTDIR)"/usr/bin
	cp -i m-gui.py "$(DESTDIR)"/usr/bin/m-gui

m-gui.1.md: README.md m-gui.1.md.head m-gui.1.md.tail
	{ cat m-gui.1.md.head; \
	  for sec in $(RM_SECTS); do \
	    sed -nr '/^## '"$$sec"'/,/^## / {s/^#+(# .*)/\U\1\L/;p}' \
	      < README.md | head -n -1 | grep -vF $(RM_SKIP); \
	  done; \
	  cat m-gui.1.md.tail; \
	} > $@

%.1: %.1.md
	pandoc -s -t man -o $@ $<

fix_mtimes:
	[ -z "$$SOURCE_DATE_EPOCH" ] || \
	  touch -d @"$$SOURCE_DATE_EPOCH" $(TOUCH)

%.rst: %.md
	grep -Ev '^\s*<!--.*-->\s*$$' $< \
	  | pandoc --from=markdown -o $@
	! grep -q raw:: $@

package: README.rst
	$(PY) setup.py sdist bdist_wheel

_publish: clean package
	read -r -p "Are you sure? "; \
	[[ "$$REPLY" == [Yy]* ]] && twine upload dist/*

# NB: run as $ make _dch OLDVERSION=a.b.c NEWVERSION=x.y.z
_dch:
	export DEBEMAIL="$$( git config --get user.email )"; \
	dch -v $(NEWVERSION) --release-heuristic log && \
	gbp dch --since v$(OLDVERSION)
