#!/usr/bin/python3

import sys
import argparse
import getpass
import socket
import logging
from urllib import request, parse
from enum import Enum

INTERNET_ACCESS_PAGE = 'internet.iitb.ac.in'
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

class ExitCode(Enum):
    SUCCESS            = 0
    BAD_INVOCATION     = 1
    CONNECTION_FAILED  = 2
    BAD_RESPONSE       = 3
    FAILURE            = 4

def get_internet_access_page():
    return 'https://' + INTERNET_ACCESS_PAGE

def is_logout_page(url):
    return True if url.split('/')[-1] == 'logout.php' else False

def get_ip(page_contents):
    '''
    Return: current IP from logout.php page contents as a string
            Throws ValueError if no IP found
    '''
    ip = page_contents.split('checked="checked"')[0].split('value=')[-1]
    ip = ip.strip(' "')
    try:
        socket.inet_aton(ip)
    except OSError:
        raise ValueError('Expected IP, got %s' % (ip))
    return ip

def do_logout():
    internet_access_page = get_internet_access_page()
    exit_code = ExitCode.SUCCESS.value
    response = request.urlopen(internet_access_page)

    if response.status != 200:
        logging.error('Connection to %s failed' % (internet_access_page))
        print('Logout failed.')
        exit_code = ExitCode.CONNECTION_FAILED.value
    elif not is_logout_page(response.geturl()):
        logging.info('Redirected to %s' % (response.geturl()))
        print('Not logged in.')
        exit_code =  ExitCode.SUCCESS.value
    else:
        try:
            logout_page = internet_access_page + '/logout.php'
            response_text = response.read().decode()
            ip = get_ip(response_text)

            data = {'ip': ip, 'button': 'Logout'}
            data = parse.urlencode(data).encode()
            logout_response = request.urlopen(logout_page, data=data)

            if logout_response.status != 200:
                logging.error('Connection to %s failed' % (logout_page))
                print('Logout failed.')
                exit_code = ExitCode.CONNECTION_FAILED.value
            else:
                print('Successfully logged out.')
        except ValueError as error:
            logging.error('Malformed data recieved from %s' % (logout_page))
            logging.info('Error message: %s' % (str(error)))
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
        print('Already logged in.')
    else:
        response = request.urlopen(login_page)
        if is_logout_page(response.geturl()):
            print('%s logged in.' % (username))
        else:
            logging.info('Redirected to %s' % (response.geturl()))
            print('Login failed.')
            exit_code = ExitCode.FAILURE.value

    return exit_code

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
                                        Tool to login and logout of IIT Bombay
                                        internet access page.''')
    options_group = parser.add_mutually_exclusive_group()
    options_group.add_argument('--logout', action='store_true', help='''
                            logout of IIT Bombay internet access page''')
    options_group.add_argument('--login', metavar='USERNAME', help='''
                            login to IIT Bombay internet access page as
                            USERNAME''')
    args = parser.parse_args()

    exit_code = ExitCode.BAD_INVOCATION.value
    if args.logout:
        exit_code = do_logout()
    elif args.login is not None:
        exit_code = do_login(args.login)
    else:
        parser.print_help()
    sys.exit(exit_code)
