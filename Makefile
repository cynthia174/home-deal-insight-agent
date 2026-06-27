.PHONY: install run test evaluate data

install:
	python -m pip install -r requirements.txt

run:
	python -m streamlit run app.py

test:
	python -m pytest -q

evaluate:
	python evaluation/evaluate.py

data:
	node scripts/build_demo_workbook.mjs

