from IPython.parallel import Client

from subprocess import Popen, PIPE


def system_call(cmd):
    """Call cmd and return (stdout, stderr, return_value).

    cmd: can be either a string containing the command to be run, or a
     sequence of strings that are the tokens of the command.

    This function is ported from QIIME (http://www.qiime.org), previously
    named qiime_system_call. QIIME is a GPL project, but we obtained permission
    from the authors of this function to port it to pyqi (and keep it under
    pyqi's BSD license).
    """
    proc = Popen(cmd,
                 universal_newlines=True,
                 shell=True,
                 stdout=PIPE,
                 stderr=PIPE)
    # communicate pulls all stdout/stderr from the PIPEs to
    # avoid blocking -- don't remove this line!
    stdout, stderr = proc.communicate()
    return_value = proc.returncode

    if return_value != 0:
        raise ValueError("Failed to execute: %s\nstdout: %s\nstderr: %s" %
                         (cmd, stdout, stderr))

    return stdout, stderr, return_value


class Context(object):
    def __init__(self, profile):
        self.client = Client(profile=profile)
        self.lview = self.client.load_balanced_view()
        self._stage_imports(self.client)

    def _stage_imports(self, cluster):
        with cluster[:].sync_imports(quiet=True):
            from moi.context import system_call  # noqa

    def submit_async(self, cmd, *args, **kwargs):
        """Submit an async command to execute

        Parameters
        ----------
        cmd : {function, str}
            A function to execute or a system call to execute
        args : list
            Arguments to pass to a function (if cmd is function)
        kwargs : dict
            Keyword arguments to pass to a function (if cmd is function)

        Returns
        -------
        IPython.parallel.client.asyncresult.AsyncResult

        """
        if isinstance(cmd, str):
            task = self.lview.apply_async(system_call, cmd)
        else:
            task = self.lview.apply_async(cmd, *args, **kwargs)

        return task
