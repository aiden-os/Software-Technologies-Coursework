#!/usr/bin/env python

# This is a simple web server for a training record application.
# It's your job to extend it by adding the backend functionality to support
# recording training in an SQL database. You will also need to support
# user access/session control. You should only need to extend this file.
# The client side code (html, javascript and css) is complete and does not
# require editing or detailed understanding, it serves only as a
# debugging/development aid.

# import the various libraries needed
import http.cookies as Cookie   # some cookie handling support
from http.server import BaseHTTPRequestHandler, HTTPServer # the heavy lifting of the web server
import urllib # some url parsing support
import json   # support for json encoding
import sys    # needed for agument handling
import time   # time support

import base64 # some encoding support
import sqlite3 # sql database
import random # generate random numbers
import time # needed to record when stuff happened
import datetime

def random_digits(n):
    """This function provides a random integer with the specfied number of digits and no leading zeros."""
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return random.randint(range_start, range_end)

# The following three functions issue SQL queries to the database.

def do_database_execute(op):
    """Execute an sqlite3 SQL query to database.db that does not expect a response."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def do_database_fetchone(op):
    """Execute an sqlite3 SQL query to database.db that expects to extract a single row result. Note, it may be a null result."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        result = cursor.fetchone()
        print(result)
        db.close()
        return result
    except Exception as e:
      print(e)
      return None

def do_database_fetchall(op):
    """Execute an sqlite3 SQL query to database.db that expects to extract a multi-row result. Note, it may be a null result."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        result = cursor.fetchall()
        print(result)
        db.close()
        return result
    except Exception as e:
        print(e)
        return None

# The following build_ functions return the responses that the front end client understands.
# You can return a list of these.

def build_response_message(code, text):
    """This function builds a message response that displays a message
       to the user on the web page. It also returns an error code."""
    return {"type":"message","code":code, "text":text}

def build_response_skill(id,name,gained,trainer,state):
    """This function builds a summary response that contains one summary table entry."""
    return {"type":"skill","id":id,"name":name, "gained":gained,"trainer":trainer,"state":state}

def build_response_class(id, name, trainer, when, notes, size, max, action):
    """This function builds an activity response that contains the id and name of an activity type,"""
    return {"type":"class", "id":id, "name":name, "trainer":trainer, "when":when, "notes":notes, "size":size, "max":max, "action":action}

def build_response_attendee(id, name, action):
    """This function builds an activity response that contains the id and name of an activity type,"""
    return {"type":"attendee", "id":id, "name":name, "action":action}

def build_response_redirect(where):
    """This function builds the page redirection response
       It indicates which page the client should fetch.
       If this action is used, it should be the only response provided."""
    return {"type":"redirect", "where":where}

# The following handle_..._request functions are invoked by the corresponding /action?command=.. request

def handle_login_request(iuser, imagic, content):
    """A user has supplied a username and password. Check if these are
       valid and if so, create a suitable session record in the database
       with a random magic identifier that is returned.
       Return the username, magic identifier and the response action set."""

    response = []
    if not iuser and not imagic:
        if 'username' in content and 'password' in content:
            username = content['username']
            password = content['password']

            try:
                query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
                user_data = do_database_fetchone(query)

                if user_data is not None:
                    iuser = user_data[0]
                    imagic = str(random_digits(8))
                    query_check_magic = f"SELECT COUNT(*) FROM session WHERE magic = '{imagic}'"
                    result_check_magic = do_database_fetchone(query_check_magic)
                    if result_check_magic[0] == 0:
                        do_database_execute(f"DELETE FROM session WHERE userid = '{iuser}'")
                        do_database_execute(f"INSERT INTO session (userid, magic) VALUES ('{iuser}', '{imagic}')")
                        response.append(build_response_redirect("/index.html"))
                    else:
                        response.append(build_response_message(298, 'Failed to generate a unique session identifier, please try again'))
                else:
                    response.append(build_response_message(200, 'Invalid username or password.'))
            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal error: ' + str(e)))
        else:
            response.append(build_response_message(100, 'A Username and Password must be provided.'))
    else:
        response.append(build_response_message(201, 'You are already logged in.'))
    return [iuser, imagic, response]

def handle_logout_request(iuser, imagic, parameters):
    """This code handles the selection of the logout button.
       You will need to ensure the end of the session is recorded in the database
       And that the session magic is revoked."""
    response = []
    try:
        query = f"SELECT userid FROM session WHERE magic = '{imagic}'"
        userid = do_database_fetchone(query)

        if userid is not None:
            do_database_execute(f"DELETE FROM session WHERE magic = '{imagic}'")
            response.append(build_response_redirect("/logout.html"))
        else:
            response.append(build_response_redirect("/login.html"))
        iuser, imagic = "!", "!"
    except Exception as e:
        print(e)
        response.append(build_response_message(299, 'Internal Error: ' + str(e)))
    return [iuser, imagic, response]

def handle_get_my_skills_request(iuser, imagic):
    """This code handles a request for a list of a users skills.
       You must return a value for all vehicle types, even when it's zero."""

    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                            SELECT
                                *
                            FROM
                                session
                            WHERE
                                userid = {iuser}
                                AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:
            try:
                current_time = int(time.time())
                query = f"""
                                    SELECT
                                        s.skillid,
                                        s.name,
                                        MAX(CASE WHEN a.userid = {iuser} AND c.start < {current_time} THEN c.start END) AS last_class_start,
                                        t.trainerid AS trainer_id,
                                        u.fullname AS trainer_name,
                                        CASE
                                            WHEN t2.trainerid = {iuser} THEN 'trainer'
                                            ELSE
                                                CASE
                                                    WHEN SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) > 0 THEN 'passed' 
                                                    WHEN SUM(CASE WHEN a.status = 0 AND c.start < {current_time} THEN 1 ELSE 0 END) > 0 THEN 'pending'
                                                    WHEN SUM(CASE WHEN a.status = 2 THEN 1 ELSE 0 END) > 0 THEN 'failed'
                                                    WHEN SUM(CASE WHEN a.status IS NULL AND c.start >= {current_time} THEN 1 ELSE 0 END) > 0 THEN 'enrolled'
                                                    ELSE 'removed'
                                                END
                                        END AS status
                                    FROM
                                        skill s
                                        LEFT JOIN class c ON s.skillid = c.skillid
                                        LEFT JOIN attendee a ON c.classid = a.classid AND a.userid = {iuser}
                                        LEFT JOIN trainer t ON s.skillid = t.skillid AND t.trainerid != {iuser}
                                        LEFT JOIN trainer t2 ON s.skillid = t2.skillid
                                        LEFT JOIN users u ON u.userid = t.trainerid and t.trainerid = trainer_id
                                    WHERE
                                        (a.status IS NOT NULL OR t.trainerid IS NOT NULL)
                                        AND (a.status = 1 OR t.trainerid != {iuser})
                                    GROUP BY
                                        s.skillid, t.trainerid
                                    ORDER BY
                                        CASE
                                            WHEN SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) > 0 THEN 1
                                            WHEN SUM(CASE WHEN a.status = 0 AND c.start < {current_time} THEN 1 ELSE 0 END) > 0 THEN 2
                                            WHEN SUM(CASE WHEN a.status = 2 THEN 1 ELSE 0 END) > 0 THEN 3
                                            WHEN SUM(CASE WHEN a.status IS NULL AND c.start >= {current_time} THEN 1 ELSE 0 END) > 0 THEN 4
                                            ELSE 5
                                        END, last_class_start DESC NULLS LAST;
                                """
                result = do_database_fetchall(query)
                if result:
                    for row in result:
                        skill_id = row[0]
                        skill_name = row[1]
                        trainer_name = row[4]
                        state = row[5]
                        gained = row[2]
                        if gained is None or state in {"pending","failed"}:
                            gained = ""
                        if state not in {"removed","enrolled"}:
                            response.append(build_response_skill(skill_id, skill_name, gained, trainer_name, state))
                    response.append(build_response_message(0, 'Skills retrieved successfully.'))
                else:
                    response.append(build_response_message(202, 'No skills found.'))

            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))
    return [iuser, imagic, response]

def handle_get_upcoming_request(iuser, imagic):
    """This code handles a request for the details of a class.
       """

    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                                SELECT
                                    *
                                FROM
                                    session
                                WHERE
                                    userid = {iuser}
                                    AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:
            try:
                current_time = int(time.time())
                query = f"""
                                SELECT
                                    c.classid,
                                    s.name AS skill,
                                    u.fullname AS trainer,
                                    c.note,
                                    c.start,
                                    c.max AS max,
                                    (
                                    CASE
                                        WHEN t.trainerid = {iuser} AND c.max != '0' THEN 'edit'
                                        WHEN a.status = '0' AND c.start > {current_time} THEN 'leave'
                                        WHEN a.status = '0' AND c.start < {current_time} THEN 'pending'
                                        WHEN a.status = '4' THEN 'cancelled'
                                        WHEN c.max = '0' THEN 'cancelled'
                                        WHEN c.max <= (
                                            SELECT COUNT(DISTINCT userid)
                                            FROM attendee a3
                                            JOIN class c3 ON a3.classid = c3.classid
                                            WHERE a3.classid = c3.classid AND a3.status = "0"
                                        ) THEN 'unavailable'
                                        ELSE 
                                            CASE
                                                WHEN EXISTS (
                                                    SELECT 1
                                                    FROM attendee a2
                                                    JOIN class c2 ON a2.classid = c2.classid
                                                    WHERE a2.userid = {iuser}
                                                        AND a2.status IN ('0','1')
                                                        AND c2.skillid = c.skillid
                                                ) THEN 'unavailable'
                                                WHEN c.start > {current_time} THEN 'join'
                                            END
                                    END 
                                    ) AS action,
                                    (
                                       SELECT COUNT(DISTINCT userid)
                                       FROM attendee a3
                                       WHERE a3.classid = c.classid AND a3.status = "0"
                                    ) AS size
                                FROM
                                    class c
                                JOIN
                                    skill s ON c.skillid = s.skillid
                                JOIN
                                    trainer t ON c.trainerid = t.trainerid
                                JOIN
                                    users u ON t.trainerid = u.userid
                                LEFT JOIN
                                    attendee a ON c.classid = a.classid AND a.userid = {iuser}
                                WHERE
                                    c.start > {current_time} 
                                GROUP BY
                                    c.classid, s.name, u.fullname, c.note, c.start, c.max, t.trainerid
                                ORDER BY
                                    c.start
                            """
                result = do_database_fetchall(query)
                for row in result:
                    class_id, skill, trainer, note, start, max_size, action, size = row
                    response.append(build_response_class(class_id, skill, trainer, start, note, size, max_size, action))

                response.append(build_response_message(0, 'Upcoming classes retrieved successfully.'))
            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))

    return [iuser, imagic, response]

def handle_get_class_detail_request(iuser, imagic, content):
    """This code handles a request for the details of a class.
       """

    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                                    SELECT
                                        *
                                    FROM
                                        session
                                    WHERE
                                        userid = {iuser}
                                        AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:
            try:
                if 'id' in content:

                    class_id = content['id']
                    current_time = int(time.time())
                    query_trainer = f"""
                                                        SELECT
                                                            t.trainerid
                                                        FROM trainer t
                                                        JOIN class c ON t.trainerid = c.trainerid
                                                        WHERE c.classid = {class_id}
                                                    """

                    result_trainer = do_database_fetchone(query_trainer)
                    print(result_trainer[0], iuser)
                    if int(result_trainer[0]) == int(iuser):
                        query_detail = f"""
                                               SELECT
                                                   c.classid = {class_id},
                                                   s.name AS skill,
                                                   u.fullname AS trainer,
                                                   c.note,
                                                   c.start,
                                                   c.max AS max,
                                                   (
                                                       SELECT COUNT(DISTINCT userid)
                                                       FROM attendee a3
                                                       WHERE a3.classid = {class_id} AND a3.status = "0"
                                                   ) AS size
                                               FROM
                                                   class c
                                               JOIN
                                                   skill s ON c.skillid = s.skillid AND c.classid = {class_id}
                                               JOIN
                                                   trainer t ON c.trainerid = t.trainerid AND c.classid = {class_id}
                                               JOIN
                                                   users u ON t.trainerid = u.userid AND c.classid = {class_id}
                                               LEFT JOIN
                                                   attendee a ON c.classid = a.classid AND a.userid = {iuser}
                                               GROUP BY
                                                   c.classid, s.name, u.fullname, c.note, c.start, c.max, t.trainerid
                                               ORDER BY
                                                   c.start
                                           """
                        result = do_database_fetchone(query_detail)
                        response.append(build_response_class(class_id, result[1], result[2], result[4], result[3], result[6], result[5], "cancel"))

                        query_attendees = f"""
                                       SELECT
                                           a.attendeeid,
                                           u.fullname AS name,
                                           CASE
                                               WHEN a.status = '0' AND c.start > {current_time} THEN 'remove'
                                               WHEN a.status = '0' AND c.start <= {current_time} THEN 'update'
                                               WHEN a.status = '1' THEN 'passed'
                                               WHEN a.status = '2' AND NOT EXISTS (
                                                   SELECT 1 FROM attendee a2
                                                   WHERE a2.userid = a.userid
                                                     AND a2.classid = a.classid
                                                     AND a2.status IN ('1', '0')
                                               ) THEN 'failed'
                                               WHEN a.status = '3' THEN 'cancelled'
                                               WHEN a.status = '4' THEN 'cancelled'
                                               WHEN c.max = '0' THEN 'cancelled'
                                               
                                           END AS action
                                       FROM
                                           attendee a
                                       JOIN
                                           users u ON a.userid = u.userid
                                       JOIN
                                           class c ON a.classid = c.classid
                                       WHERE
                                           c.classid = {class_id}
                                       ORDER BY
                                           u.fullname
                                   """
                        result_attendees = do_database_fetchall(query_attendees)
                        print(result_attendees)
                        attendees = []
                        for row in result_attendees:
                            attendee_id, name, action = row
                            attendees.append(build_response_attendee(attendee_id, name, action))
                        response.extend(attendees)
                        response.append(build_response_message(0, 'Class details retrieved successfully.'))
                    else:
                        response.append(build_response_message(223, 'You are not a trainer for this skill.'))
                else:
                    response.append(build_response_message(101, 'Missing parameter: classid'))
            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))

    return [iuser, imagic, response]


def handle_join_class_request(iuser, imagic, content):
    """This code handles a request by a user to join a class.
      """
    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                                        SELECT
                                            *
                                        FROM
                                            session
                                        WHERE
                                            userid = {iuser}
                                            AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:
            try:
                if 'id' in content:
                    class_id = content['id']
                    query_class_availability = f"""
                                SELECT
                                    CASE
                                        WHEN c.start > {int(time.time())} AND c.max > (
                                                SELECT COUNT(DISTINCT userid)
                                                FROM attendee a
                                                JOIN class c2 ON a.classid = c2.classid
                                               WHERE a.classid = c2.classid AND a.status = "0"
                                            ) THEN 'join'
                                            ELSE 'unavailable'
                                    END AS action
                                FROM class c
                                WHERE c.classid = {class_id}
                            """

                    result_availability = do_database_fetchone(query_class_availability)

                    if result_availability and result_availability[0] == 'join':
                        query_user_eligibility = f"""
                                    SELECT
                                        CASE
                                            WHEN EXISTS (
                                                SELECT 1
                                                FROM attendee a
                                                JOIN class c ON a.classid = c.classid
                                                WHERE a.userid = {iuser}
                                                    AND a.status IN ('0', '1')
                                                    AND c.skillid = (
                                                        SELECT skillid FROM class WHERE classid = {class_id}
                                                    )
                                            ) THEN 0
                                            WHEN EXISTS (
                                                SELECT 1
                                                FROM attendee a
                                                WHERE a.userid = {iuser}
                                                    AND a.classid = {class_id}
                                                    AND a.status = '4'
                                            ) THEN 0
                                            ELSE 1
                                        END AS can_join
                                """

                        result_user_eligibility = do_database_fetchone(query_user_eligibility)

                        if result_user_eligibility and result_user_eligibility[0] == 1:
                            query_update_class_size = f"""
                                        UPDATE class
                                        SET size = size + 1
                                        WHERE classid = {class_id}
                                    """
                            do_database_execute(query_update_class_size)

                            query_add_user_to_class = f"""
                                        INSERT INTO attendee (userid, classid, status)
                                        VALUES ({iuser}, {class_id}, '0')
                                    """
                            do_database_execute(query_add_user_to_class)
                            try:
                                current_time = int(time.time())
                                query = f"""
                                                SELECT
                                                    c.classid,
                                                    s.name AS skill,
                                                    u.fullname AS trainer,
                                                    c.note,
                                                    c.start,
                                                    c.max AS max,
                                                    (
                                                    CASE
                                                        WHEN t.trainerid = {iuser} AND c.max != '0' THEN 'edit'
                                                        WHEN a.status = '0' AND c.start > {current_time} THEN 'leave'
                                                        WHEN a.status = '0' AND c.start < {current_time} THEN 'pending'
                                                        WHEN a.status = '4' THEN 'cancelled'
                                                        WHEN c.max = '0' THEN 'cancelled'
                                                        ELSE 
                                                            CASE
                                                                WHEN EXISTS (
                                                                    SELECT 1
                                                                    FROM attendee a2
                                                                    JOIN class c2 ON a2.classid = c2.classid
                                                                    WHERE a2.userid = {iuser}
                                                                        AND a2.status IN ('0','1')
                                                                        AND c2.skillid = c.skillid
                                                                ) THEN 'unavailable'
                                                                WHEN c.start > {current_time} THEN 'join'
                                                            END
                                                    END 
                                                    ) AS action,
                                                    (
                                                        SELECT COUNT(DISTINCT userid)
                                                        FROM attendee a3
                                                        WHERE a3.classid = c.classid AND a3.status = "0"
                                                    ) AS size
                                                FROM
                                                    class c
                                                JOIN
                                                    skill s ON c.skillid = s.skillid
                                                JOIN
                                                    trainer t ON c.trainerid = t.trainerid
                                                JOIN
                                                    users u ON t.trainerid = u.userid
                                                LEFT JOIN
                                                    attendee a ON c.classid = a.classid AND a.userid = {iuser}
                                                WHERE
                                                    c.start > {current_time} AND c.classid = {class_id}
                                                GROUP BY
                                                    c.classid, s.name, u.fullname, c.note, c.start, c.max, t.trainerid
                                                ORDER BY
                                                    c.start
                                            """

                                result = do_database_fetchall(query)

                                for row in result:
                                    class_id, skill, trainer, note, start, max_size, action, size = row
                                    response.append(
                                        build_response_class(class_id, skill, trainer, start, note, size, max_size, action))
                            except Exception as e:
                                print(e)
                                response.append(build_response_message(299, 'Internal Error: ' + str(e)))
                            response.append(build_response_message(0, 'You have successfully joined the class.'))
                        else:
                            response.append(build_response_message(203, 'You are not eligible to join this class.'))
                    else:
                        response.append(build_response_message(204, 'This class is not available for joining.'))
                else:
                    response.append(build_response_message(104, 'Missing parameter: classid'))
            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))

    return [iuser, imagic, response]

def handle_leave_class_request(iuser, imagic, content):
    """This code handles a request by a user to leave a class.
    """
    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                                            SELECT
                                                *
                                            FROM
                                                session
                                            WHERE
                                                userid = {iuser}
                                                AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:
            try:
                if 'id' in content:
                    class_id = content['id']

                    query_class_availability = f"""
                                    SELECT
                                        CASE
                                            WHEN c.start > {int(time.time())} THEN 'leave'
                                            ELSE 'unavailable'
                                        END AS action
                                    FROM class c
                                    WHERE c.classid = {class_id}
                                """

                    result_availability = do_database_fetchone(query_class_availability)

                    if result_availability and result_availability[0] == 'leave':
                        query_user_eligibility = f"""
                            SELECT
                                CASE
                                    WHEN EXISTS (
                                        SELECT 1
                                        FROM attendee a
                                        JOIN class c ON a.classid = c.classid
                                        WHERE a.userid = {iuser}
                                            AND a.status = '0' 
                                            AND c.skillid = (
                                                SELECT skillid FROM class WHERE classid = {class_id}
                                            )
                                    ) THEN 1 
                                    ELSE 0  
                                END AS can_leave
                        """

                        result_user_eligibility = do_database_fetchone(query_user_eligibility)

                        if result_user_eligibility and result_user_eligibility[0] == 1:

                            query_remove_user_from_class = f"""
                                UPDATE attendee
                                SET status = '3'
                                WHERE userid = {iuser}
                                    AND classid = {class_id}
                            """
                            do_database_execute(query_remove_user_from_class)
                            try:
                                current_time = int(time.time())
                                query = f"""
                                                    SELECT
                                                        c.classid,
                                                        s.name AS skill,
                                                        u.fullname AS trainer,
                                                        c.note,
                                                        c.start,
                                                        c.max AS max,
                                                        (
                                                        CASE
                                                            WHEN t.trainerid = {iuser} AND c.max != '0' THEN 'edit'
                                                            WHEN a.status = '0' AND c.start > {current_time} THEN 'leave'
                                                            WHEN a.status = '0' AND c.start < {current_time} THEN 'pending'
                                                            WHEN a.status = '4' THEN 'cancelled'
                                                            WHEN c.max = '0' THEN 'cancelled'
                                                            ELSE 
                                                                CASE
                                                                    WHEN EXISTS (
                                                                        SELECT 1
                                                                        FROM attendee a2
                                                                        JOIN class c2 ON a2.classid = c2.classid
                                                                        WHERE a2.userid = {iuser}
                                                                            AND a2.status IN ('0','1')
                                                                            AND c2.skillid = c.skillid
                                                                    ) THEN 'unavailable'
                                                                    WHEN c.start > {current_time} THEN 'join'
                                                                END
                                                        END 
                                                        ) AS action,
                                                        (
                                                            SELECT COUNT(DISTINCT userid)
                                                            FROM attendee a3
                                                            WHERE a3.classid = c.classid AND a3.status = "0"
                                                        ) AS size
                                                    FROM
                                                        class c
                                                    JOIN
                                                        skill s ON c.skillid = s.skillid
                                                    JOIN
                                                        trainer t ON c.trainerid = t.trainerid
                                                    JOIN
                                                        users u ON t.trainerid = u.userid
                                                    LEFT JOIN
                                                        attendee a ON c.classid = a.classid AND a.userid = {iuser}
                                                    WHERE
                                                        c.start > {current_time}
                                                    GROUP BY
                                                        c.classid, s.name, u.fullname, c.note, c.start, c.max, t.trainerid
                                                    ORDER BY
                                                        c.start
                                                """

                                result = do_database_fetchall(query)

                                for row in result:
                                    class_id, skill, trainer, note, start, max_size, action, size = row
                                    response.append(build_response_class(class_id, skill, trainer, start, note, size , max_size, action))
                                response.append(build_response_message(0, 'You have successfully left the class.'))
                            except Exception as e:
                                print(e)
                                response.append(build_response_message(299, 'Internal Error: ' + str(e)))
                        else:
                            response.append(build_response_message(205, 'You are not eligible to leave this class.'))
                    else:
                        response.append(build_response_message(206, 'This class is not available for leaving.'))
                else:
                    response.append(build_response_message(104, 'Missing parameter: classid'))
            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))

    return [iuser, imagic, response]


def handle_cancel_class_request(iuser, imagic, content):
    """This code handles a request to cancel an entire class."""

    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                                            SELECT
                                                *
                                            FROM
                                                session
                                            WHERE
                                                userid = {iuser}
                                                AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:

            try:
                if 'id' in content:
                    class_id = content['id']
                    query_check_trainer = f"""
                                                SELECT
                                                    c.start,
                                                    t.trainerid
                                                FROM
                                                    class c
                                                JOIN
                                                    trainer t ON c.trainerid = t.trainerid
                                                WHERE
                                                    c.classid = {class_id}
                                                """

                    # Execute the query to check if the user is the trainer and process the result
                    result_check_trainer = do_database_fetchone(query_check_trainer)
                    if result_check_trainer:
                        start_time, trainer_id = result_check_trainer
                        current_time = int(time.time())
                        if int(trainer_id) == int(iuser):
                            if start_time > current_time:
                                do_database_execute(f"UPDATE class SET max = 0 WHERE classid = {class_id}")
                                do_database_execute(f"UPDATE class SET max = 0 WHERE classid = {class_id}")
                                do_database_execute(f"UPDATE attendee SET status = '3' WHERE classid = {class_id}")

                                query_updated_class = f"""
                                                       SELECT
                                                           c.classid = {class_id},
                                                           s.name AS skill,
                                                           u.fullname AS trainer,
                                                           c.note,
                                                           c.start,
                                                           c.max AS max,
                                                           (
                                                               SELECT COUNT(DISTINCT userid)
                                                               FROM attendee a3
                                                               WHERE a3.classid = {class_id} AND a3.status = "0"
                                                           ) AS size
                                                       FROM
                                                           class c
                                                       JOIN
                                                           skill s ON c.skillid = s.skillid AND c.classid = {class_id}
                                                       JOIN
                                                           trainer t ON c.trainerid = t.trainerid AND c.classid = {class_id}
                                                       JOIN
                                                           users u ON t.trainerid = u.userid AND c.classid = {class_id}
                                                       LEFT JOIN
                                                           attendee a ON c.classid = a.classid AND a.userid = {iuser}
                                                       WHERE
                                                           c.start > {current_time}
                                                       GROUP BY
                                                           c.classid, s.name, u.fullname, c.note, c.start, c.max, t.trainerid
                                                       ORDER BY
                                                           c.start
                                           """

                                result = do_database_fetchone(query_updated_class)
                                response.append(build_response_class(result[0], result[1], result[2], result[4], result[3], result[6], result[5], "cancelled"))

                                query_update_attendees = f"""
                                                           SELECT
                                                               a.attendeeid,
                                                               u.fullname AS name,
                                                               CASE
                                                                   WHEN a.status = '0' AND c.start > {current_time} THEN 'remove'
                                                                   WHEN a.status = '0' AND c.start <= {current_time} THEN 'update'
                                                                   WHEN a.status = '1' THEN 'passed'
                                                                   WHEN a.status = '2' AND NOT EXISTS (
                                                                       SELECT 1 FROM attendee a2
                                                                       WHERE a2.userid = a.userid
                                                                         AND a2.classid = a.classid
                                                                         AND a2.status IN ('1', '0')
                                                                   ) THEN 'failed'
                                                                   WHEN a.status = '3' THEN 'cancelled'
                                                                   WHEN a.status = '4' THEN 'cancelled'
                                                                   WHEN c.max = '0' THEN 'cancelled'
                                                                   
                                                               END AS action
                                                           FROM
                                                               attendee a
                                                           JOIN
                                                               users u ON a.userid = u.userid
                                                           JOIN
                                                               class c ON a.classid = c.classid
                                                           WHERE
                                                               c.classid = {class_id}
                                                           ORDER BY
                                                               u.fullname
                                                       """

                                result_updated_attendees = do_database_fetchall(query_update_attendees)
                                print(result_updated_attendees)
                                attendees = []
                                for row in result_updated_attendees:
                                    attendee_id, name, action = row
                                    attendees.append(build_response_attendee(attendee_id, name, action))

                                response.extend(attendees)

                                response.append(build_response_message(0, 'Class cancelled successfully.'))
                            else:
                                # Class has already started, cannot cancel
                                print(start_time, current_time)
                                response.append(build_response_message(206, 'Cannot cancel a class that has already started.'))
                        else:
                            # User is not the trainer
                            response.append(build_response_message(207, 'You are not the trainer for this class.'))
                    else:
                        # Class not found
                        response.append(build_response_message(208, 'Class not found.'))
                else:
                    response.append(build_response_message(105, 'Missing parameter: id'))
            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))

    return [iuser, imagic, response]

def handle_update_attendee_request(iuser, imagic, content):
    """This code handles a request to cancel a user attendance at a class by a trainer"""

    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                                            SELECT
                                                *
                                            FROM
                                                session
                                            WHERE
                                                userid = {iuser}
                                                AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:
            try:
                if 'id' in content and 'state' in content:
                    attendee_id = content['id']
                    new_state = content['state']

                    query_check_trainer = f"""
                                                   SELECT
                                                       a.userid,
                                                       a.status,
                                                       c.trainerid,
                                                       c.start,
                                                       u.fullname, 
                                                       c.classid
                                                   FROM
                                                       attendee a
                                                   JOIN
                                                       class c ON a.classid = c.classid
                                                   JOIN
                                                       users u ON a.userid = u.userid
                                                   WHERE
                                                       a.attendeeid = {attendee_id}
                                                   """

                    result_check_trainer = do_database_fetchone(query_check_trainer)

                    if result_check_trainer:
                        user_id, current_state, trainer_id, start_time, user_fullname, class_id = result_check_trainer
                        current_time = int(time.time())
                        if int(trainer_id) == int(iuser):
                            if int(start_time) <= current_time:
                                if new_state in {'pass', 'fail'}:

                                    if new_state == 'pass':
                                        do_database_execute(f"UPDATE attendee SET status = '1' WHERE attendeeid = {attendee_id}")
                                        update_state = 'passed'
                                    elif new_state == 'fail':
                                        do_database_execute(f"UPDATE attendee SET status = '2' WHERE attendeeid = {attendee_id}")
                                        update_state = 'failed'
                                    query_update_attendee = f"""
                                                                                           SELECT
                                                                                               a.attendeeid,
                                                                                               u.fullname AS name
                                                                                           FROM
                                                                                               attendee a
                                                                                           JOIN
                                                                                               users u ON a.userid = u.userid
                                                                                           JOIN
                                                                                               class c ON a.classid = c.classid
                                                                                           WHERE
                                                                                               c.classid = {class_id}
                                                                                          ORDER BY
                                                                                               u.fullname
                                                                                       """

                                    result_updated_attendee = do_database_fetchone(query_update_attendee)
                                    print(result_updated_attendee)
                                    #attendees = []
                                    #for row in result_updated_attendees:
                                   #     attendee_id, name, action = row
                                    #    attendees.append(build_response_attendee(attendee_id, name, action))

                                    response.append(build_response_attendee(result_updated_attendee[0], result_updated_attendee[1], update_state))
                                    response.append(build_response_message(0, 'Attendee status updated successfully.'))
                                else:
                                    response.append(build_response_message(210, 'Invalid state provided.'))
                            else:
                                if new_state == 'remove':
                                    do_database_execute(f"UPDATE attendee SET status = '4' WHERE attendeeid = {attendee_id}")
                                    query_updated_class = f"""
                                                           SELECT
                                                               c.classid = {class_id},
                                                               s.name AS skill,
                                                               u.fullname AS trainer,
                                                               c.note,
                                                               c.start,
                                                               c.max AS max,
                                                               (
                                                                   SELECT COUNT(DISTINCT userid)
                                                                   FROM attendee a3
                                                                   WHERE a3.classid = {class_id} AND a3.status = "0"
                                                               ) AS size
                                                           FROM
                                                               class c
                                                           JOIN
                                                               skill s ON c.skillid = s.skillid AND c.classid = {class_id}
                                                           JOIN
                                                               trainer t ON c.trainerid = t.trainerid AND c.classid = {class_id}
                                                           JOIN
                                                               users u ON t.trainerid = u.userid AND c.classid = {class_id}
                                                           LEFT JOIN
                                                               attendee a ON c.classid = a.classid AND a.userid = {iuser}
                                                           WHERE
                                                               c.start > {current_time}
                                                           GROUP BY
                                                               c.classid, s.name, u.fullname, c.note, c.start, c.max, t.trainerid
                                                           ORDER BY
                                                               c.start
                                               """

                                    result_updated_class = do_database_fetchone(query_updated_class)
                                    response.append(build_response_class(result_updated_class[0], result_updated_class[1], result_updated_class[2], result_updated_class[4], result_updated_class[3], result_updated_class[6], result_updated_class[5], "cancel"))

                                    query_update_attendees = f"""
                                                           SELECT
                                                               a.attendeeid,
                                                               u.fullname AS name,
                                                               CASE
                                                                   WHEN a.status = '0' AND c.start > {current_time} THEN 'remove'
                                                                   WHEN a.status = '0' AND c.start <= {current_time} THEN 'update'
                                                                   WHEN a.status = '1' THEN 'passed'
                                                                   WHEN a.status = '2' AND NOT EXISTS (
                                                                       SELECT 1 FROM attendee a2
                                                                       WHERE a2.userid = a.userid
                                                                         AND a2.classid = a.classid
                                                                         AND a2.status IN ('1', '0')
                                                                   ) THEN 'failed'
                                                                   WHEN a.status = '3' THEN 'cancelled'
                                                                   WHEN a.status = '4' THEN 'cancelled'
                                                                   WHEN c.max = '0' THEN 'cancelled'
    
                                                               END AS action
                                                           FROM
                                                               attendee a
                                                           JOIN
                                                               users u ON a.userid = u.userid
                                                           JOIN
                                                               class c ON a.classid = c.classid
                                                           WHERE
                                                               c.classid = {class_id}
                                                           ORDER BY
                                                               u.fullname
                                                       """

                                    result_updated_attendees = do_database_fetchall(query_update_attendees)
                                    attendees = []
                                    for row in result_updated_attendees:
                                        attendee_id, name, action = row
                                        attendees.append(build_response_attendee(attendee_id, name, action))

                                    response.extend(attendees)
                                    response.append(build_response_message(0, 'Attendee status updated successfully.'))
                                else:
                                    response.append(build_response_message(210, 'Invalid state provided.'))


                        else:
                            response.append(build_response_message(211, 'You are not the trainer for this class.'))
                    else:
                        response.append(build_response_message(212, 'Attendee not found.'))
                else:
                    response.append(build_response_message(106, 'Missing parameters: id or state'))
            except Exception as e:
                print(e)
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))

    return [iuser, imagic, response]

def handle_create_class_request(iuser, imagic, content):
    """This code handles a request to create a class."""

    response = []

    if not iuser or not imagic:
        response.append(build_response_redirect("/login.html"))
    else:
        query_check_login = f"""
                                            SELECT
                                                *
                                            FROM
                                                session
                                            WHERE
                                                userid = {iuser}
                                                AND magic = '{imagic}'"""
        result_check_login = do_database_fetchone(query_check_login)
        if not result_check_login:
            response.append(build_response_redirect("/login.html"))
        else:
            try:
                if 'id' in content and 'note' in content and 'max' in content and 'day' in content and 'month' in content and 'year' in content and 'hour' in content and 'minute' in content:
                    skill_id = content['id']
                    class_note = content['note']
                    max_size = content['max']
                    day = content['day']
                    month = content['month']
                    year = content['year']
                    hour = content['hour']
                    minute = content['minute']
                    print(content['note'])
                    try:
                        date_time = datetime.datetime(year, month, day, hour, minute)
                        class_start = int(time.mktime(date_time.timetuple()))
                        current_time = int(time.time())
                    except ValueError as ve:
                        response.append(build_response_message(213, f'Invalid date or time: {ve}'))
                    if class_start > current_time:
                        query_check_trainer = f"""
                                                SELECT
                                                    trainerid 
                                                FROM
                                                    trainer
                                                WHERE
                                                    skillid = {skill_id}
                                                """

                        result_check_trainer = do_database_fetchone(query_check_trainer)
                        if int(result_check_trainer[0]) == int(iuser):
                            if max_size in range(1,10):
                                try:
                                    query_insert_class = f"""
                                                    INSERT INTO class (trainerid, skillid, start, max, note)
                                                    VALUES ({iuser}, {skill_id}, {class_start}, {max_size}, '{class_note}' )
                                                    """
                                except Exception as e:
                                    print(e)
                                    response.append(build_response_message(299, 'Internal Error: ' + str(e)))
                                do_database_execute(query_insert_class)
                                query_classid = f"""
                                                SELECT
                                                    MAX(classid)
                                                FROM
                                                    class
                                                """
                                result_insert_class = do_database_fetchone(query_classid)
                                if result_insert_class:
                                    class_id = result_insert_class[0]
                                    response.append(build_response_redirect(f'/class/{class_id}'))
                                else:
                                    response.append(build_response_message(213, 'Failed to create class.'))
                            else:
                                response.append(build_response_message(214, 'Class size must be between 1 and 10.'))
                        else:
                            if result_check_trainer:
                                response.append(build_response_message(215, 'You are not a trainer for this skill.'))
                                print(result_check_trainer[0], iuser)
                            else:
                                response.append(build_response_message(216, 'Skill not found.'))
                    else:
                        response.append(build_response_message(217, 'Class start time must be in the future.'))
                else:
                    response.append(build_response_message(107, 'Missing parameters: id, note, max, day, month, year, hour, minute'))
            except Exception as e:
                response.append(build_response_message(299, 'Internal Error: ' + str(e)))
    return [iuser, imagic, response]

# HTTPRequestHandler class
class myHTTPServer_RequestHandler(BaseHTTPRequestHandler):

    # POST This function responds to GET requests to the web server.
    def do_POST(self):

        # The set_cookies function adds/updates two cookies returned with a webpage.
        # These identify the user who is logged in. The first parameter identifies the user
        # and the second should be used to verify the login session.
        def set_cookies(x, user, magic):
            ucookie = Cookie.SimpleCookie()
            ucookie['u_cookie'] = user
            x.send_header("Set-Cookie", ucookie.output(header='', sep=''))
            mcookie = Cookie.SimpleCookie()
            mcookie['m_cookie'] = magic
            x.send_header("Set-Cookie", mcookie.output(header='', sep=''))

        # The get_cookies function returns the values of the user and magic cookies if they exist
        # it returns empty strings if they do not.
        def get_cookies(source):
            rcookies = Cookie.SimpleCookie(source.headers.get('Cookie'))
            user = ''
            magic = ''
            for keyc, valuec in rcookies.items():
                if keyc == 'u_cookie':
                    user = valuec.value
                if keyc == 'm_cookie':
                    magic = valuec.value
            return [user, magic]

        # Fetch the cookies that arrived with the GET request
        # The identify the user session.
        user_magic = get_cookies(self)

        print(user_magic)

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # The special file 'action' is not a real file, it indicates an action
        # we wish the server to execute.
        if parsed_path.path == '/action':
            self.send_response(200) #respond that this is a valid page request

            # extract the content from the POST request.
            # This are passed to the handlers.
            length =  int(self.headers.get('Content-Length'))
            scontent = self.rfile.read(length).decode('ascii')
            print(scontent)
            if length > 0 :
              content = json.loads(scontent)
            else:
              content = []

            # deal with get parameters
            parameters = urllib.parse.parse_qs(parsed_path.query)
            if 'command' in parameters:
                # check if one of the parameters was 'command'
                # If it is, identify which command and call the appropriate handler function.
                # You should not need to change this code.
                if parameters['command'][0] == 'login':
                    print("content:", content, "user_magic:", user_magic)
                    [user, magic, response] = handle_login_request(user_magic[0], user_magic[1], content)
                    #The result of a login attempt will be to set the cookies to identify the session.
                    set_cookies(self, user, magic)
                elif parameters['command'][0] == 'logout':
                    print("content:", parameters, "user_magic:", user_magic)
                    [user, magic, response] = handle_logout_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'get_my_skills':
                    [user, magic, response] = handle_get_my_skills_request(user_magic[0], user_magic[1])
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'get_upcoming':
                    [user, magic, response] = handle_get_upcoming_request(user_magic[0], user_magic[1])
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'join_class':
                    [user, magic, response] = handle_join_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'leave_class':
                    [user, magic, response] = handle_leave_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'get_class':
                    [user, magic, response] = handle_get_class_detail_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'update_attendee':
                    [user, magic, response] = handle_update_attendee_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'cancel_class':
                    [user, magic, response] = handle_cancel_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'create_class':
                    [user, magic, response] = handle_create_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                else:
                    # The command was not recognised, report that to the user. This uses a special error code that is not part of the codes you will use.
                    response = []
                    response.append(build_response_message(901, 'Internal Error: Command not recognised.'))

            else:
                # There was no command present, report that to the user. This uses a special error code that is not part of the codes you will use.
                response = []
                response.append(build_response_message(902,'Internal Error: Command not found.'))

            text = json.dumps(response)
            print(text)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(text, 'utf-8'))

        else:
            # A file that does n't fit one of the patterns above was requested.
            self.send_response(404) # a file not found html response
            self.end_headers()
        return

   # GET This function responds to GET requests to the web server.
   # You should not need to change this function.
    def do_GET(self):

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # Return a CSS (Cascading Style Sheet) file.
        # These tell the web client how the page should appear.
        if self.path.startswith('/css'):
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())

        # Return a Javascript file.
        # These contain code that the web client can execute.
        elif self.path.startswith('/js'):
            self.send_response(200)
            self.send_header('Content-type', 'text/js')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())

        # A special case of '/' means return the index.html (homepage)
        # of a website
        elif parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/index.html', 'rb') as file:
                self.wfile.write(file.read())

        # Pages of the form /create/... will return the file create.html as content
        # The ... will be a class id
        elif parsed_path.path.startswith('/class/'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/class.html', 'rb') as file:
                self.wfile.write(file.read())

        # Pages of the form /create/... will return the file create.html as content
        # The ... will be a skill id
        elif parsed_path.path.startswith('/create/'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/create.html', 'rb') as file:
                self.wfile.write(file.read())

        # Return html pages.
        elif parsed_path.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages'+parsed_path.path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            # A file that does n't fit one of the patterns above was requested.
            self.send_response(404)
            self.end_headers()

        return

def run():
    """This is the entry point function to this code."""
    print('starting server...')
    ## You can add any extra start up code here
    # Server settings
    # When testing you should supply a command line argument in the 8081+ range

    # Changing code below this line may break the test environment. There is no good reason to do so.
    if(len(sys.argv)<2): # Check we were given both the script name and a port number
        print("Port argument not provided.")
        return
    server_address = ('127.0.0.1', int(sys.argv[1]))
    httpd = HTTPServer(server_address, myHTTPServer_RequestHandler)
    print('running server on port =',sys.argv[1],'...')
    httpd.serve_forever() # This function will not return till the server is aborted.

run()
