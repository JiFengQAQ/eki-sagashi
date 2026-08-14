.PHONY: data test deploy clean

data:
	cd pipeline && python3 build_data.py

test:
	cd pipeline && python3 -m pytest tests/ -q
	cd web && node --test tests/*.mjs

test-py:
	cd pipeline && python3 -m pytest tests/ -q

test-js:
	cd web && node --test tests/*.mjs

deploy: data
	sudo rsync -a --delete web/ /var/www/eki-sagashi/
	sudo chown -R www-data:www-data /var/www/eki-sagashi/
	@echo "deployed to /var/www/eki-sagashi/"

clean:
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
