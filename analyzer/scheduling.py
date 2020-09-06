from nltk.corpus import stopwords as nltk_stopwords

from analyzer.analysis.analyzers import (TermFrequencyAnalyzer,
                                         StemmingTokenizer)
from analyzer.analysis.stopwords import stopwords
from analyzer.analysis.tasks import async_process_document


class MultiDocAnalyzer:
    """
    Responsible for scheduling the analysis of a set of documents and
    aggregating the results.

    Offers callbacks to inform the user about the status of the
    analysis. Useful for long running processes.

    Base class. Override & implement `perform_analysis`
    """

    def __init__(self, docs, language, stem=False):
        """
        :param list docs: A list of documents (paths) to analyze
        :param str language: The language of the documents
        :param bool stem: Whether to analyze in words or stems
        """
        self._docs = docs
        self._progress = {
            'total': len(self._docs),
            'completed': 0,
            'details': {
                doc: {'processed': False, 'results': None}
                for doc in self._docs
            }
        }
        self._language = language
        self._started = False
        self._stem = stem
        # load additional stopwords for english to improve results
        # pre-loads stopwords to avoid having each analyzer process
        # them internally since they are the same
        tokenizer = StemmingTokenizer(self._language, stem=self._stem)
        if self._language == 'english':
            self._stopwords = set([processed_sw for sw in stopwords
                               for processed_sw in tokenizer(sw)])
        else:
            self._stopwords = set([processed_sw for sw in
                               nltk_stopwords.words(self._language)
                               for processed_sw in tokenizer(sw)])


    def perform_analysis(self):
        """
        Not implemented. Override to implement
        """
        raise NotImplementedError

    def _mark_doc_processed(self, doc, results):
        """
        Marks a doc as processed, storing its results & updating
        internal data structures

        :param str doc: the filename
        :param dict results: A dictionary with the results of the
            document analysis
        """

        self._progress['details'][doc] = {
            'processed': True,
            'results': results
        }
        self._progress['completed'] = self._progress['completed'] + 1

    def check_progress(self):
        """
        Returns whether analysis is done or not.

        :rtype tuple(bool, int): A tuple indicating if the analysis is
            completed (result[0]) and how many documents are completed
            (result[1])
        """
        return (self._progress['completed'] < self._progress['total'],
                self._progress['completed'])

    def combine_output(self):
        """
        Takes care of combining similarly structured output from
        different analyzers.

        :rtype list: A list of dictionaries with the combined output,
        sorted by most frequent to least frequent.
        Looks like this:
            [
                {
                    <term>: {
                        'count': <how many times this term occured>,
                        'documents': [<doc1>, ..]
                        'sentences': [<sentence1>, ..]
                },
                ...
            ]
        """
        combined_output = {}
        in_progress, _ = self.check_progress()
        if in_progress:
            raise ValueError("Still processing!")
        for doc, doc_details in self._progress['details'].items():
            for term, values in doc_details['results'].items():
                existing_data = combined_output.get(term)
                if existing_data:
                    combined_data = {
                        'count': existing_data['count'] + values['count'],
                        'documents': existing_data['documents'] + [doc],
                        'sentences': (existing_data['sentences'] +
                                      values['sentences'])
                    }
                else:
                    combined_data = {
                        'count': values['count'],
                        'documents': [doc],
                        'sentences': values['sentences']
                    }

                combined_output[term] = combined_data

        return sorted(combined_output.items(), key=lambda x: x[1]['count'],
                      reverse=True)

    def analysis_success(self):
        """
        Returns if the analysis was successful or if a document's analysis
        failed

        :rtype tuple(bool, list): A tuple:
            (<whether_any_documents_failed>, [<failed_doc1>, ...])
        """
        in_progress, _ = self.check_progress()
        if in_progress:
            return (False, [])

        return (all([v['processed']
                     for v in self._progress['details'].values()]),
                [key for key, value in self._progress['details'].items()
                  if value['results'] is None])


class SyncMultiDocAnalyzer(MultiDocAnalyzer):
    """
    A `MultiDocAnalyzer` that analyzes docs 1-1.
    """

    def perform_analysis(self):
        in_progress, _ = self.check_progress()
        if not in_progress:
            return

        next_doc = next(iter(set(self._docs) -
                             set([doc for doc, status in
                                  self._progress['details'].items()
                                  if status['processed']])))
        with open(next_doc, 'r') as ff:
            doc_content = ff.read()
        doc_analyzer = TermFrequencyAnalyzer(doc_content,
                                             self._language,
                                             stem=self._stem,
                                             stopwords=self._stopwords)
        results = doc_analyzer.analyze_document()
        self._mark_doc_processed(next_doc, results)


class AsyncMultiDocAnalyzer(MultiDocAnalyzer):
    """
    A `MultiDocAnalyzer` that analyzes docs asynchronously,
    using Celery in the background.
    """

    def __init__(self, *args, **kwargs):
        self._started = False
        self._tasks = {}
        super().__init__(*args, **kwargs)

    def perform_analysis(self):
        """
        Fires asynchronous (celery tasks). Stores them internally
        and updates their status.
        """
        in_progress, _ = self.check_progress()
        if not in_progress:
            return
        if self._started:
            for doc, task in self._tasks.items():
                if task and task.ready():
                    result = task.get()
                    self._mark_doc_processed(doc, result)
                    self._tasks[doc] = None

        else:
            self._started = True
            for doc in self._docs:
                with open(doc, 'r') as ff:
                    doc_content = ff.read()
                task = async_process_document.delay(doc_content,
                                                    self._language,
                                                    self._stem,
                                                    list(self._stopwords))
                self._tasks[doc] = task
