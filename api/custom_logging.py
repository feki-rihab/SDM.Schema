#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##
# Copyright 2024 FIWARE Foundation, e.V.
#
# This file is part of SDM SQL schema generator
#
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
##
# Custom Logger Using Loguru

from logging import Handler, currentframe, __file__, basicConfig, getLogger
import sys
from pathlib import Path
from loguru import logger
from json import load


class InterceptHandler(Handler):
    loglevel_mapping = {
        50: "CRITICAL",
        40: "ERROR",
        30: "WARNING",
        20: "INFO",
        10: "DEBUG",
        0: "NOTSET",
    }

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except AttributeError:
            level = self.loglevel_mapping[record.levelno]

        frame, depth = currentframe(), 2
        while frame.f_code.co_filename == __file__:
            frame = frame.f_back
            depth += 1

        log = logger.bind(request_id="app")
        log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class CustomizeLogger:
    @classmethod
    def make_logger(cls, config_path: Path):
        config = cls.load_logging_config(config_path)
        logging_config = config.get("logger")

        logger = cls.customize_logging(
            filepath=logging_config.get("path"),
            level=logging_config.get("level"),
            retention=logging_config.get("retention"),
            rotation=logging_config.get("rotation"),
            format=logging_config.get("format"),
        )

        return logger

    @classmethod
    def customize_logging(cls, filepath: Path, level: str, rotation: str, retention: str, format: str):

        logger.remove()

        logger.add(sys.stdout, enqueue=True, backtrace=True, level=level.upper(), format=format)

        logger.add(
            str(filepath),
            rotation=rotation,
            retention=retention,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=format,
        )

        basicConfig(handlers=[InterceptHandler()], level=0)
        getLogger("uvicorn.access").handlers = [InterceptHandler()]

        for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
            _logger = getLogger(_log)
            _logger.handlers = [InterceptHandler()]

        return logger.bind(request_id=None, method=None)

    @classmethod
    def load_logging_config(cls, config_path):
        config = None
        with open(config_path) as config_file:
            config = load(config_file)
        return config

    def get_logger(self):
        # filename = join(dirname(dirname(__file__)), 'logs', 'app.log')
        #
        # basicConfig(filename=filename,
        #             filemode='w',
        #             format='%(name)s - %(levelname)s - %(message)s',
        #             level=DEBUG)
        #
        # logging = getLogger(__name__)
        #
        # return logging
        #
        logging_config_path = Path.cwd().joinpath("common/config.json")
        customize_logger = CustomizeLogger.make_logger(logging_config_path)

        return customize_logger
