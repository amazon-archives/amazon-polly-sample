# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("boto3").setLevel(logging.WARNING)


import boto3
import os
import feedparser
from boto3 import Session
from boto3 import resource
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
from HTMLParser import HTMLParser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
import datetime
import dateutil.parser
import hashlib

MAX_TPS = 10
MAX_CONCURENT_CONNECTIONS = 20
TASKS = 100
REQUEST_LIMIT = 1200


def split_content_by_dot(soup, max_len):
    """
    split HTML soup into parts not bigger than max_len may break prosody where
    dot is not at the end of the sentence (like "St. Louis") in some cases may
    be synthesized as two separate sentences
    """
    text = soup.get_text(" ", strip=True)
    start = 0
    while start < len(text):
        if len(text) - start <= max_len:
            yield text[start:]
            return
        max = start + max_len
        index = text.rfind(".", start, max)
        if index == start:
            start += 1
        elif index < 0:
            yield text[start:max]
            start = max
        else:
            yield text[start:index]
            start = index


def get_entries(feed):
    NEW_POST = u"""New post, author {author}, title {title} {content}"""
    for entry in feed.entries:
        if "http" in entry.id:
            nid = hashlib.md5(str(entry.id))
            entry.id = nid.hexdigest()
        entry_content = entry.content[0].value
        soup = BeautifulSoup(entry_content, 'html.parser')
        chunks = split_content_by_dot(soup, REQUEST_LIMIT-len(NEW_POST))
        chunks = list(chunks)
        published = dateutil.parser.parse(entry.published)
        for i, chunk in enumerate(chunks):
            if i == 0:
                chunk = NEW_POST.format(
                        author=entry.author,
                        title=entry.title,
                        content=chunk)
            yield dict(
                content=chunk,
                id="%s_%d" % (entry.id, i),
                title=entry.title,
                published=published - datetime.timedelta(0, i),
            )
            remaining = chunk


def lambda_handler(event, context):
    rss = event['rss']
    bucket_name = event['bucket']
    logging.info("Processing url: %s" % rss)
    logging.info("Using bucket: %s" % bucket_name)

    session = Session(region_name="us-west-2")
    polly = session.client("polly")
    s3 = resource('s3')
    bucket = s3.Bucket(bucket_name)

    logging.info("getting list of existing objects in the given bucket")
    files = set(o.key for o in bucket.objects.all())

    feed = feedparser.parse(rss)

    title = feed['feed']['title']
    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.title('Audio podcast based on: %s' % title)
    fg.link(href=feed.feed.link, rel='alternate')
    fg.subtitle(feed.feed.description)

    ENTRY_URL = "http://{bucket}.s3-website.{region}.amazonaws.com/{filename}"

    for entry in get_entries(feed):
        filename = "%s.mp3" % entry['id']
        fe = fg.add_entry()
        fe.id(entry['id'])
        fe.title(entry['title'])
        fe.published(entry['published'])
        entry_url = ENTRY_URL.format(bucket=bucket_name, filename=filename, region=os.environ["AWS_REGION"])
        fe.enclosure(entry_url, 0, 'audio/mpeg')
        if filename in files:
            logging.info('Article "%s" with id %s already exist, skipping.'
                         % (entry['title'], entry['id']))
            continue
        try:
            logging.info("Next entry, size: %d" % len(entry['content']))
            logging.debug("Content: %s" % entry['content'])
            response = polly.synthesize_speech(
                    Text=entry['content'],
                    OutputFormat="mp3",
                    VoiceId="Joanna")
            with closing(response["AudioStream"]) as stream:
                bucket.put_object(Key=filename, Body=stream.read())
        except BotoCoreError as error:
            logging.error(error)
    bucket.put_object(Key='podcast.xml', Body=fg.rss_str(pretty=True))
