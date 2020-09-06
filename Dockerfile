FROM python:3.8.5-buster AS analyzer

RUN mkdir -p /usr/app 
WORKDIR /usr/app

RUN alias python=python3


COPY ./ /usr/app

RUN pip install -r ./requirements.txt

RUN python -c 'import nltk; nltk.download("stopwords"); nltk.download("punkt")'

CMD ["/bin/sh"]
