#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wordpress Client
"""

from ConfigParser import SafeConfigParser, Error
import logging
import oursql
from sqlite3 import DatabaseError, OperationalError, connect
import os
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods.users import GetUsers


class WordPressClient(object):
    def get_blog_subscribers(self):
        """ Gets WordPress Blog Subscribers """
        config = SafeConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        try:
            url = config.get("wordpress", "url")
            username = config.get("wordpress", "username")
            password = config.get("wordpress", "password")
        except Error as error:
            msg = "Config section [wordpress] bad or missing: %s" % \
                  error.message
            logging.error(msg)
            raise Exception(msg)

        subs = []

        wp = Client(url, username, password)
        users = wp.call(GetUsers())
        logging.info("Found %d users." % len(users))
        for u in users:
            logging.debug("User: %s" % u.email)
            logging.debug("Roles: %s" % u.roles)
            if 'subscriber' in u.roles:
                subs.append((u.email, u.first_name))
        return subs

    def get_blog_unubscribers(self):
        pass


class WordPressDBClient(object):
    def __init__(self):
        config = SafeConfigParser()
        try:
            config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        except Error:
            msg = "config.ini file bad or missing"
            logging.error(msg)
            raise Exception(msg)
        try:
            self.username = config.get("wordpressdb", "user")
            self.password = config.get("wordpressdb", "password")
            self.host = config.get("wordpressdb", "host")
            self.db = config.get("wordpressdb", "db")
        except Error:
            msg = "Config section [wordpressdb] bad or missing"
            logging.error(msg)
            raise Exception(msg)

        con = None

        try:
            con = connect(os.path.join(os.path.dirname(__file__), 'sender.db'))
            cur = con.cursor()
            logging.info("Creating table wp_subs if absent...")

            cur.execute(('''CREATE TABLE IF NOT EXISTS wp_subs
                (id integer primary key, email text, display_name text,
                created_at datetime)'''))

            cur.execute(
                ('''CREATE UNIQUE INDEX IF NOT EXISTS `ix_email`
                    ON `wp_subs` (`email` ASC)'''))

            con.commit()
            cur.close()
        except OperationalError, msg:
            logging.error(msg)
            raise
        except DatabaseError, msg:
            logging.error(msg)
            raise
        finally:
            if con is not None:
                con.close()

    def get_blog_subscribers(self):
        """ Gets WordPress Blog Subscribers """
        logging.info("Getting blog subscribers.")
        conn = oursql.connect(host=self.host, user=self.username,
                              passwd=self.password, db=self.db)
        curs = conn.cursor(oursql.DictCursor)

        sql = (
            "SELECT users.user_email, users.display_name "
            "FROM admin_wpdb.wp_usermeta meta "
            "INNER JOIN admin_wpdb.wp_users users ON "
            "   (users.ID = meta.user_id) "
            "WHERE meta.meta_key = 'wp_capabilities' "
            "AND meta.meta_value LIKE '%subscriber%' "
            "ORDER BY users.ID")

        logging.debug(sql)

        try:
            curs.execute(sql)
        except Error as error:
            logging.error(error.message)
            raise Exception(error.message)

        users = []

        rows = curs.fetchall()
        for row in rows:
            user = (row['user_email'], row['display_name'])
            logging.debug(user)
            users.append(user)

        logging.info("Found %d total blog subscribers." % len(users))

        return users

    def add_wp_sub_local(self, email, display_name):
        """ Adds WordPress Subscriber to local DB """
        logging.info("Adding blog subscriber %s if absent.", email)
        con = None
        try:
            con = connect(os.path.join(os.path.dirname(__file__), 'sender.db'))
            cur = con.cursor()
            sql = '''INSERT OR IGNORE INTO wp_subs
                (email, display_name, created_at) VALUES (?, ?, datetime())'''
            # logging.info(sql)
            cur.execute(sql, (email, display_name))
            con.commit()
            cur.close()
        except OperationalError, msg:
            logging.error(msg)
            raise
        except DatabaseError, msg:
            logging.error(msg)
            raise
        finally:
            if con is not None:
                con.close()

    def delete_wp_sub_local(self, email):
        """ Adds WordPress Subscriber to local DB """
        logging.info("Adding blog subscriber %s if absent.", email)
        con = None
        try:
            con = connect(os.path.join(os.path.dirname(__file__), 'sender.db'))
            cur = con.cursor()
            sql = "DELETE FROM wp_subs WHERE email = ?"
            cur.execute(sql, (email))
            con.commit()
            cur.close()
        except OperationalError, msg:
            logging.error(msg)
            raise
        except DatabaseError, msg:
            logging.error(msg)
            raise
        finally:
            if con is not None:
                con.close()

    def get_blog_unsubscribers(self):
        """Gets disjoint set of WordPress subscribers and local subscribers"""
        subscribers = self.get_blog_subscribers()
        # subscribers.pop()  # test unsub
        wp_subs = self.get_wp_subs_local()
        unsubs = {}
        try:
            unsubs = set(wp_subs).difference(subscribers)
        except TypeError as error:
            logging.info("Error %s", error)
        finally:
            logging.info("Found %d unsubscribers.", len(unsubs))
            return unsubs

    def get_wp_subs_local(self):
        """ Gets WordPress Subscribers from local DB """
        logging.info("Getting local blog subscribers")
        users = []
        try:
            con = connect(os.path.join(os.path.dirname(__file__), 'sender.db'))
            cur = con.cursor()
            cur.execute("SELECT email, display_name FROM wp_subs")
            rows = cur.fetchall()
            for row in rows:
                user = (row[0], row[1])
                logging.debug(user)
                users.append(user)
            con.commit()
            cur.close()
        except OperationalError, msg:
            logging.error(msg)
            raise
        except DatabaseError, msg:
            logging.error(msg)
            raise
        finally:
            if con is not None:
                con.close()

        logging.info("Found %d total local blog subscribers." % len(users))
        return users

    def seed_wp_subs_local(self):
        """ Seed local wp_subs table with subs from Wordpress """
        logging.info("Seeding wp_subs in local db")
        subs = self.get_blog_subscribers()
        for sub in subs:
            logging.info("Adding email %s", sub[0])
            self.add_wp_sub_local(sub[0], sub[1])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)
    wp = WordPressDBClient()
    subs = wp.get_wp_subs_local()
    if subs is None or len(subs) == 0:
        wp.seed_wp_subs_local()
    unsubs = wp.get_blog_unsubscribers()
    logging.info(unsubs)
