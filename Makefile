.PHONY : install clean

install :
	python3 -m venv venv
	venv/bin/pip install -r requirements.pip

clean :
	rm -rf venv
