test:
	PYTHONPATH=src python -m unittest discover -s tests -v

validate-sample:
	PYTHONPATH=src python -m voc.cli validate data/sample/service_case_feedback.csv service_case_feedback
