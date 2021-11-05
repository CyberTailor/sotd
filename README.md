Server of the Day
=================

> Documentation:
> [sotd\_submission.py(8)](https://docs.sysrq.in/sotd_submission.py.8),
> [sotd.py(8)](https://docs.sysrq.in/sotd.py)

Installation
------------
Both programs use Python standard library only and don't require any external
dependencies.

Run the following commands if you're installing sotd for the first time:

```
# make user
# make install-db
# make install
```

This will create "gemini" user and group, install skeleton database and files
and then install CGI application and email bot.

### Email submissions

OpenSMTPD config file snippet to enable email submissions:

```smtpd.conf
action "bot.sotd" mda "/usr/local/bin/sotd_submission.py" user "gemini" alias <aliases>
match from any for rcpt-to "sotd@CHANGEME" action "bot.sotd"
```

Suggestions:

* Install [Rspamd](https://rspamd.com) to enforce email policies (see
  `misc/rspamd.groups.conf`)
* Install [logrotate](https://github.com/logrotate/logrotate) to setup log.gmi
  rotation (see `misc/sotd.logrotate`).

Submissions for new servers need to be approved manually by editing registry
file.

Contributing
------------
Patches and pull requests are welcome. Please use either [git-send-email(1)][1]
or [git-request-pull(1)][2], addressed to <cyber@sysrq.in>.

[1]: https://git-send-email.io/
[2]: https://git-scm.com/docs/git-request-pull
