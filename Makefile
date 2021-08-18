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
	@echo  'intall		- Run the former two targets'
	@echo  'install-info	- Copy files from skel/ to $(CGIDIR)/info'
	@echo  '		  Run this only when installing the first time!'

install: install-bot install-cgi

install-bot:
	mkdir -p $(DESTDIR)$(BINDIR)
	$(INSTALL) sotd_submission.py $(DESTDIR)$(BINDIR)

install-cgi:
	mkdir -p $(DESTDIR)$(CGIDIR)/cgi-bin
	$(INSTALL_CGI) sotd.py $(DESTDIR)$(CGIDIR)/cgi-bin
	-$(PYTHON) -m compileall -q -f -d $(CGIDIR)/cgi-bin $(DESTDIR)$(CGIDIR)/cgi-bin
	-$(PYTHON) -O -m compileall -q -f -d $(CGIDIR)/cgi-bin $(DESTDIR)$(CGIDIR)/cgi-bin
	-$(PYTHON) -OO -m compileall -f -d $(CGIDIR)/cgi-bin $(DESTDIR)$(CGIDIR)/cgi-bin

install-info:
	mkdir -p $(DESTDIR)$(CGIDIR)/info
	$(INSTALL_CGI_DATA) skel/lang.desc $(DESTDIR)$(CGIDIR)/info
	$(INSTALL_CGI_DATA) skel/features.desc $(DESTDIR)$(CGIDIR)/info
	$(INSTALL_CGI_DATA) skel/registry $(DESTDIR)$(CGIDIR)/info

.PHONY: help install install-cgi install-info
