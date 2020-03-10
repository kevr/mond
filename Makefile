
ifeq ($(DESTDIR),)
	DESTDIR="/"
endif

ifeq ($(PREFIX),)
	PREFIX="usr/local"
endif

install:
	install -m0755 ./src/mond.py $(DESTDIR)/$(PREFIX)/bin/mond

uninstall:
	rm -f $(DESTDIR)/$(PREFIX)/bin/mond

