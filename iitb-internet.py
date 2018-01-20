#!/usr/bin/python3

import sys
import argparse
import getpass
import socket
import logging
import urllib
from enum import Enum
from urllib import parse as urllib_parse
from urllib import error as urllib_error
from urllib import request as urllib_request

INTERNET_ACCESS_PAGE = 'internet.iitb.ac.in'
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

class ExitCode(Enum):
    SUCCESS            = 0
    FAILURE            = 1
    BAD_INVOCATION     = 2
    CONNECTION_FAILED  = 3
    BAD_RESPONSE       = 4
    UNKNOWN_ERROR      = 5

def get_login_page():
    return 'https://' + INTERNET_ACCESS_PAGE + '/index.php'

def get_logout_page():
    return 'https://' + INTERNET_ACCESS_PAGE + '/logout.php'

def is_logout_page(url):
    return True if url.split('/')[-1] == 'logout.php' else False

def get_response(url, data=None):
    '''
    Arguments:

    url  -- String containing the URL to fetch.
    data -- Dict with additional data to be sent to the server (default: None).

    Return: HTTPResponse object received on fetching the url.

    Raises: ConnectionError if connection failed or when response code not 200.
    '''
    if data is not None:
        data = urllib_parse.urlencode(data).encode()
    try:
        response = urllib_request.urlopen(url, data=data)
    except urllib_error.URLError as e:
        raise ConnectionError('Connection to %s failed.' % (url)) from e
    if response.getcode() != 200:
        raise ConnectionError(
                'Received response code %d, Connection to %s failed.'
                % (response.getcode(), url))
    return response

def get_response_text(response):
    '''
    Arguments:

    response -- HTTPResponse object.

    Returns: String containing the page contents.

    Raises: ValueError on error while decoding page contents.
    '''
    try:
        response_data = response.read()
        return response_data.decode()
    except ValueError as e:
        raise ValueError('Malfromed data recieved from %s.'
                % (response.geturl())) from e

def is_banned(page_contents):
    return ("window.location.href='https://internet.iitb.ac.in/baned.php'"
            in page_contents)

def is_bad_password(page_contents):
    return ("window.location.href='https://internet.iitb.ac.in/badpw.php'"
            in page_contents)

def get_user(page_contents):
    '''
    Returns: current user logged in from logout page contents as a string.
    '''
    user = (page_contents.split('checked="checked"')[0]
                .split('<tr>')[-1]
                .split('</center>')[0].strip()
                .split()[-1])
    return user

def get_ip(page_contents):
    '''
    Returns: current IP from logout page contents as a string.

    Raises: ValueError if no IP found.
    '''
    ip = page_contents.split('checked="checked"')[0].split('value=')[-1]
    ip = ip.strip(' "')
    try:
        socket.inet_aton(ip)
    except OSError as e:
        raise ValueError('Expected IP, got %s' % (ip)) from e
    return ip

def get_login_status():
    '''
    Returns: (login_stauts, user, ip) tuple

    login_status -- True if logged into IIT Bombay Internet Access Page and
                    False otherwise.
    user         -- String containing the username logged in at IIT Bombay
                    Internet Access Page or None if login_status is False.
    ip           -- String containing the ip from which the current machine
                    is logged in or None if login_status is False.

    Raises: ConnectionError, ValueError
    '''
    login_page = get_login_page()
    response = get_response(login_page)
    if not is_logout_page(response.geturl()):
        return (False, None, None)
    else:
        page_contents = get_response_text(response)
        user = get_user(page_contents)
        ip = get_ip(page_contents)
        return (True, user, ip)


def do_logout():
    '''
    Returns: (logout_status, message) tuple

    logout_status -- True if logging out of IIT Bombay Internet access Page
                     successful and False otherwise.
    message       -- A string message explaining what happened.

    Raises: ConnectionError, ValueError
    '''
    logged_in, user, ip = get_login_status()
    if not logged_in:
        return (False, 'Cannot logout. Not logged in.')

    logout_page = get_logout_page()
    data = {'ip': ip, 'button': 'Logout'}
    _ = get_response(logout_page, data)
    logged_in, _, _ = get_login_status()
    if logged_in:
        return (False, 'Logout failed. Still logged in as %s.' % (user))
    else:
        return (True, 'Successfully logged out %s.' % (user))

def do_login(username, password):
    '''
    Arguments:

    username -- A string representing the username for login.
    password -- A string containing the password of the username for login.

    Returns: (login_status, message) tuple

    logout_status -- True if logging into IIT Bombay Internet access Page
                     as username successful and False otherwise.
    message       -- A string message explaining what happened.

    Raises: ConnectionError, ValueError
    '''
    logged_in, user, _ = get_login_status()
    if logged_in:
        return (False, 'Already logged in as %s.' % (user))

    login_page = get_login_page()
    data = {'uname': username, 'passwd': password}
    response = get_response(login_page, data)
    response_text = get_response_text(response)
    banned = is_banned(response_text)
    bad_password = is_bad_password(response_text)

    if banned:
        return (False, 'Login not required.')
    elif bad_password:
        return (False, 'Login failed. Password incorrect.')

    logged_in, user, _ = get_login_status()
    if not logged_in:
        return (False, 'Login failed due to unknown error.')
    else:
        return (True, 'Successfully logged in as %s.' % (user))

if __name__ == '__main__':
    exit_code = ExitCode.SUCCESS
    parser = argparse.ArgumentParser(add_help=False, description='''
                                        Tool to login and logout of IIT Bombay
                                        internet access page.''')
    options_group = parser.add_mutually_exclusive_group()
    options_group.add_argument('--status', action='store_true', help='''
                            current login status''')
    options_group.add_argument('--logout', action='store_true', help='''
                            logout of IIT Bombay internet access page''')
    options_group.add_argument('--login', metavar='USERNAME', help='''
                            login to IIT Bombay internet access page as
                            USERNAME''')
    options_group.add_argument('--help', '-h', action='store_true', help='''
                            show this help message and exit''')
    try:
        args = parser.parse_args()
    except SystemExit:
        parser.exit(status=ExitCode.BAD_INVOCATION.value)

    msg = 'Command Failed. Check error logs for more information.'
    try:
        if args.logout:
            logged_out, msg = do_logout()
            if not logged_out:
                exit_code = ExitCode.FAILURE
        elif args.login is not None:
            password = getpass.getpass(prompt="Enter password: ")
            logged_in, msg = do_login(args.login, password)
            if not logged_in:
                exit_code = ExitCode.FAILURE
        elif args.help:
            parser.print_help()
        else:
            logged_in, user, _ = get_login_status()
            if logged_in:
                msg = ('Logged in as %s.' % (user))
            else:
                msg = 'Not logged in.'
    except ConnectionError as e:
        logging.exception(e)
        exit_code = ExitCode.CONNECTION_FAILED
    except ValueError as e:
        logging.exception(e)
        exit_code = ExitCode.BAD_RESPONSE
    except Exception as e:
        logging.exception(e)
        exit_code = ExitCode.UNKNOWN_ERROR
    print(msg)
    sys.exit(exit_code.value)
