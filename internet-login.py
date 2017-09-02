#!/usr/bin/python3

import sys
import argparse
import getpass
import socket
import logging
from urllib import request, parse
from enum import Enum

INTERNET_ACCESS_PAGE_NAME = 'internet.iitb.ac.in'
INTERNET_ACCESS_PAGE_IP = '10.201.250.201'

class ExitCode(Enum):
    SUCCESS = 0
    BAD_INVOCATION = 1
    CONNECTION_FAILED = 2
    BAD_RESPONSE = 3
    FAILURE = 4

def check_dns():
    try:
        ip_addr = socket.gethostbyname(INTERNET_ACCESS_PAGE_NAME)
        return True
    except socket.gaierror:
        logging.warning('DNS lookup for %s failed. Using preset IP %s' %
                            (INTERNET_ACCESS_PAGE_NAME, INTERNET_ACCESS_PAGE_IP))
        return False

def get_internet_access_page():
    internet_access_page = INTERNET_ACCESS_PAGE_NAME
    if not check_dns():
        internet_access_page = INTERNET_ACCESS_PAGE_IP
    return 'https://' + internet_access_page

def is_logout_page(url):
    return True if url.split('/')[-1] == 'logout.php' else False

def do_logout():
    internet_access_page = get_internet_access_page()
    exit_code = ExitCode.SUCCESS.value
    response = request.urlopen(internet_access_page)

    if response.status != 200:
        logging.error('Connection to %s failed' % (internet_access_page))
        print('Logout failed.')
        exit_code = ExitCode.CONNECTION_FAILED.value
    elif not is_logout_page(response.geturl()):
        logging.warning('Redirected to %s' % (response.geturl()))
        print('Not logged in.')
        exit_code =  ExitCode.SUCCESS.value
    else:
        try:
            logout_page = internet_access_page + '/logout.php'
            response_text = response.read().decode()
            ip = response_text.split('checked="checked"')[0].split('value=')[-1]
            ip = ip.strip(' "')
            socket.inet_aton(ip)

            data = {'ip': ip, 'button': 'Logout'}
            data = parse.urlencode(data).encode()
            logout_response = request.urlopen(logout_page, data=data)
            if logout_response.status != 200:
                logging.error('Connection to %s failed' % (logout_page))
                print('Logout failed.')
                exit_code = ExitCode.CONNECTION_FAILED.value
            else:
                print('Successfully logged out.')
        except (OSError, ValueError) as error:
            logging.error('Malformed data recieved from %s' % (logout_page))
            logging.error('Error message: %s' % (str(error)))
            print('Logout failed.')
            exit_code = ExitCode.BAD_RESPONSE.value
    return exit_code

def do_login(username):
    login_page = get_internet_access_page() + '/index.php'
    exit_code = ExitCode.SUCCESS.value

    password = getpass.getpass(prompt="Enter password: ")
    data = {'uname': username, 'passwd': password}
    data = parse.urlencode(data).encode()
    response = request.urlopen(login_page, data=data)
    if response.status != 200:
        logging.error('Connection to %s failed' % (login_page))
        print('Login failed.')
        exit_code = ExitCode.CONNECTION_FAILED.value
    elif is_logout_page(response.geturl()):
        print('% already logged in.')
    else:
        response = request.urlopen(login_page)
        if is_logout_page(response.geturl()):
            print('%s logged in' % (username))
        else:
            logging.warning('Redirected to %s' % (response.geturl()))
            print('Login failed.')
            exit_code = ExitCode.FAILURE.value

    return exit_code

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
                                        Tool to login and logout of IIT Bombay
                                        internet access page.''')
    parser.add_argument('--logout', action='store_true', help='''
                            logout of IIT Bombay internet access page''')
    parser.add_argument('--user', help='''
                            username used to login to IIT Bombay internet
                            access page''')
    args = parser.parse_args()

    exit_code = ExitCode.BAD_INVOCATION.value
    if args.logout:
        exit_code = do_logout()
    elif args.user is not None:
        exit_code = do_login(args.user)
    else:
        parser.print_help()
    sys.exit(exit_code)
