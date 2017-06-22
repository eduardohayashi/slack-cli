import argparse
import os
import stat
import sys

import appdirs
import slacker


SLACK_TOKEN_PATH = os.path.join(appdirs.user_config_dir("slack-cli"), "slack_token")


def get_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-t", "--token",
                        help=("Slack token which will be saved to {}. This argument only needs to be" +
                              " specified once.").format(SLACK_TOKEN_PATH))
    return parser

def parse_args(parser):
    """
    Parse cli arguments; eventually save the token to disk.
    """
    args = parser.parse_args()
    try:
        token = _get_token(args.token)
    except UndefinedSlackToken:
        sys.stderr.write(
"""Empty slack token value. You must define a valid Slack token to interact
with the Slack API. You may do do either by defining the SLACK_TOKEN
environment variable or by writing the token to {}.\n""".format(SLACK_TOKEN_PATH))
        sys.exit(1)

    # Save token
    if not os.path.exists(SLACK_TOKEN_PATH):
        token_directory = os.path.dirname(SLACK_TOKEN_PATH)
        if not os.path.exists(token_directory):
            os.makedirs(token_directory)
        with open(SLACK_TOKEN_PATH, "w") as slack_token_file:
            slack_token_file.write(token)
        os.chmod(SLACK_TOKEN_PATH, stat.S_IREAD | stat.S_IWRITE)

    return args, token

def _get_token(token):
    token = token or os.environ.get('SLACK_TOKEN')
    if not token:
        token = os.environ.get('SLACK_TOKEN')
    if not token:
        try:
            with open(SLACK_TOKEN_PATH) as slack_token_file:
                token = slack_token_file.read().strip()
        except IOError:
            pass
    if not token:
        raise UndefinedSlackToken
    return token


class UndefinedSlackToken(Exception):
    pass


def is_destination_valid(channel=None, group=None, user=None):
    """
    Raise a ValueError if zero or more than one destinations are selected.
    """
    if channel is None and group is None and user is None:
        raise ValueError("You must define one of channel, group or user argument.")
    if len([a for a in (channel, group, user) if a is not None]) > 1:
        raise ValueError("You must define only one of channel, group or user argument.")

def get_source_id(token, source_name):
    destination = get_sources(token, [source_name])
    if not destination:
        raise ValueError(u"Channel, group or user '{}' does not exist".format(source_name))
    return destination[0]["id"]

def get_source_ids(token, source_names):
    return {
        s['id']: s['name'] for s in get_sources(token, source_names)
    }

def get_sources(token, source_names):
    def filter_objects(objects):
        return [
            obj for obj in objects if len(source_names) == 0 or obj['name'] in source_names
        ]

    sources = []
    sources += filter_objects(slacker.Channels(token).list().body['channels'])
    sources += filter_objects(slacker.Groups(token).list().body['groups'])
    sources += filter_objects(slacker.Users(token).list().body['members'])
    return sources


class ChatAsUser(slacker.Chat):

    def post_formatted_message(self, destination_id, text, pre=False):
        if pre:
            text = "```" + text + "```"
        text = text.strip()
        self.post_message(destination_id, text, as_user=True)