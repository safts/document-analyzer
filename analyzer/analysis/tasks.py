from .analyzers import TermFrequencyAnalyzer
from ..celery import app


@app.task(name='async_process_document')
def async_process_document(doc, language, stem, stopwords):
    doc_analyzer = TermFrequencyAnalyzer(doc,
                                         language,
                                         stem=stem,
                                         stopwords=stopwords)
    return doc_analyzer.analyze_document()
