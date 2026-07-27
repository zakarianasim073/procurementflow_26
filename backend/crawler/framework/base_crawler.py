"""Compatibility shim — the real BaseCrawler lives in plugins/base.py.

This file previously contained a stale copy of app_crawler_combined.py content
that caused a circular self-import (it imported BaseCrawler from itself then
redefined it). Any code that does ``from crawler.framework.base_crawler import
BaseCrawler`` now gets the canonical implementation transparently.
"""
from __future__ import annotations

from ..plugins.base import BaseCrawler, CrawlContext  # noqa: F401

__all__ = ["BaseCrawler", "CrawlContext"]
