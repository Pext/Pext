# git_describe.py
#
# Dulwich is dual-licensed under the Apache License, Version 2.0 and the GNU
# General Public License as public by the Free Software Foundation; version 2.0
# or (at your option) any later version. You can redistribute it and/or
# modify it under the terms of either of these two licenses.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# You should have received a copy of the licenses; if not, see
# <http://www.gnu.org/licenses/> for a copy of the GNU General Public License
# and <http://www.apache.org/licenses/LICENSE-2.0> for a copy of the Apache
# License, Version 2.0.
#

"""Describe the repository version in a similar way to git describe."""

import datetime
import time

from dulwich.repo import Repo


def describe(directory):
    """Describe the repository version in a similar way to git describe.

    :param projdir: git repository root
    :returns: a string description of the current git version, similar to git describe

    Examples: "abcdefg", "v0.1" or "v0.1-5-abcdefg".
    """
    # Get the repository
    with Repo(directory) as repo:
        # Get a list of all tags
        refs = repo.get_refs()
        tags = {}
        for key, value in refs.items():
            key = key.decode()
            obj = repo.get_object(value)
            if u'tags' not in key:
                continue

            _, tag = key.rsplit(u'/', 1)

            try:
                commit = obj.object
            except AttributeError:
                continue
            else:
                commit = repo.get_object(commit[1])
            tags[tag] = [
                datetime.datetime(*time.gmtime(commit.commit_time)[:6]),
                commit.id.decode('utf-8'),
            ]

        sorted_tags = sorted(tags.items(), key=lambda tag: tag[1][0], reverse=True)

        # If there are no tags, return the current commit
        if len(sorted_tags) == 0:
            return "g{}".format(repo[repo.head()].id.decode('utf-8')[:7])

        # We're now 0 commits from the top
        commit_count = 0

        # Get the latest commit
        latest_commit = repo[repo.head()]

        # Walk through all commits
        walker = repo.get_walker()
        for entry in walker:
            # Check if tag
            commit_id = entry.commit.id.decode('utf-8')
            for tag in sorted_tags:
                tag_name = tag[0]
                tag_commit = tag[1][1]
                if commit_id == tag_commit:
                    if commit_count == 0:
                        return tag_name
                    else:
                        return "{}-{}-g{}".format(tag_name, commit_count + 1, latest_commit.id.decode('utf-8')[:7])

            commit_count += 1

        # We couldn't find the latest tag in the history, so return the commit (fallback)
        return "g{}".format(latest_commit.id.decode('utf-8')[:7])
