#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wordpress Client
"""

from ConfigParser import SafeConfigParser, Error
import logging
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods.users import GetUsers


class WordPressClient(object):
    def get_blog_subscribers(self):
        """ Gets WordPress Blog Subscribers """
        config = SafeConfigParser()
        config.read('config.ini')

        try:
            url = config.get("wordpress", "url")
            username = config.get("wordpress", "username")
            password = config.get("wordpress", "password")
        except Error as error:
            msg = "Config section [wordpress] bad or missing: %s" % \
                  error.message
            logging.error(msg)
            raise Exception(msg)

        wp = Client(url, username, password)
        users = wp.call(GetUsers())
        logging.info("Found %d users." % len(users))
        for u in users:
            logging.debug("User: %s" % u.email)
            logging.debug("Roles: %s" % u.roles)
            if 'subscriber' in u.roles:
                # TODO send email
                logging.info("Sending email to %s" % u.email)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
    # console handler with specified log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(console_handler)
    wp = WordPressClient()
    wp.get_blog_subscribers()
