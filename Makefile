PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin

CGIDIR   ?= /var/gemini/sotd
CGIUSER  ?= gemini
CGIGROUP ?= gemini

PYTHON ?= /usr/bin/env python

INSTALL          = install
INSTALL_CGI      = $(INSTALL) -o $(CGIUSER) -g $(CGIGROUP)
INSTALL_CGI_DATA = $(INSTALL_CGI) -m 0644 -b

help:
	@echo  'usage: make [target] ...'
	@echo
	@echo  'targets:'
	@echo  'install-bot	- Install sotd_sumbission.py email bot'
	@echo  'install-cgi	- Install sotd.py to $(CGIDIR)/cgi-bin'
	@echo  'install		- Run the former two targets'
	@echo  'user		- Add $(CGIUSER) user to the system'
	@echo  'install-db	- Install empty sotd.db database to $(CGIDIR)'

install: install-bot install-cgi

user:
	groupadd $(CGIGROUP)
	useradd -d /var/gemini -s /sbin/nologin -u $(CGIUSER) -g $(CGIGROUP)

install-bot:
	mkdir -p $(DESTDIR)$(BINDIR)
	$(INSTALL) sotd_submission.py $(DESTDIR)$(BINDIR)

install-cgi:
	mkdir -p $(DESTDIR)$(CGIDIR)/cgi-bin
	$(INSTALL_CGI) sotd.py $(DESTDIR)$(CGIDIR)/cgi-bin
	-$(PYTHON) -m compileall -q -f -d $(CGIDIR)/cgi-bin $(DESTDIR)$(CGIDIR)/cgi-bin
	-$(PYTHON) -O -m compileall -q -f -d $(CGIDIR)/cgi-bin $(DESTDIR)$(CGIDIR)/cgi-bin
	-$(PYTHON) -OO -m compileall -f -d $(CGIDIR)/cgi-bin $(DESTDIR)$(CGIDIR)/cgi-bin

install-db:
	rm -f sotd.db
	sqlite3 sotd.db <create_db.sql
	$(INSTALL_CGI) -d $(DESTDIR)$(CGIDIR)/info
	$(INSTALL_CGI_DATA) skel/registry $(DESTDIR)$(CGIDIR)/info
	$(INSTALL_CGI_DATA) skel/log.gmi $(DESTDIR)$(CGIDIR)/info
	$(INSTALL_CGI_DATA) sotd.db $(DESTDIR)$(CGIDIR)/info

.PHONY: help install install-cgi install-db
