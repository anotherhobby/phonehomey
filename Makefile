install_dependencies:
	pip install -r requirements.pip --src .

clean:
	rm -rf prowlpy
	rm -rf *.pyc