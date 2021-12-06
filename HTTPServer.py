import json
from socketserver import ThreadingMixIn
from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
import os
from os.path import (join, exists, abspath, isdir, split, splitdrive)
from os import getcwd, curdir, pardir, fstat
from urllib.parse import quote, unquote
from posixpath import normpath
from io import StringIO
import re
import cgi
import socket
import errno

DATA_DIR = getcwd()

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class RequestHandler(SimpleHTTPRequestHandler):
    """ Handler to handle POST requests for actions.
    """

    serve_path = DATA_DIR

    def do_HEAD(self):
        """ Override do_HEAD to handle HTTP Range requests. """
        self.range_from, self.range_to = self._get_range_header()
        if self.range_from is None:
            # nothing to do here
            return SimpleHTTPRequestHandler.do_HEAD(self)
        f = self.send_range_head()
        if f:
            f.close()

    def do_GET(self):
        """ Overridden to handle HTTP Range requests. """
        self.range_from, self.range_to = self._get_range_header()
        if self.path == "/status":
            self.send_response(200)
            self.end_headers()
            status = {"file_watched_percentage" : self.server.watched_percentage}
            self.wfile.write(json.dumps(status).encode())
            return None
        if self.range_from is None:
            # nothing to do here
            return SimpleHTTPRequestHandler.do_GET(self)
        f, f_size = self.send_range_head()
        if f:
            self.copy_file_range(f, self.wfile, f_size)
            f.close()

    def copy_file_range(self, in_file, out_file, in_file_size):
        """ Copy only the range in self.range_from/to. """
        in_file.seek(self.range_from)
        # Add 1 because the range is inclusive
        bytes_to_copy = 1 + self.range_to - self.range_from
        buf_length = 1024 * 1024 * 5
        bytes_copied = 0
        try:
            while bytes_copied < bytes_to_copy:
                if self.server.piece_range:
                    self.server.is_available(hash, self.server.piece_range[0], self.server.piece_range[1], self.server.piece_size, self.range_from + bytes_copied, self.range_from + bytes_copied + buf_length)
                read_buf = in_file.read(min(buf_length, bytes_to_copy-bytes_copied))
                if len(read_buf) == 0:
                    break
                out_file.write(read_buf)
                bytes_copied += len(read_buf)
        except ConnectionResetError:
            pass
        finally:
            self.server.watched_percentage = (self.range_from + bytes_copied) / in_file_size
        return bytes_copied

    def send_range_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = join(path, index)
                if exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)

        if not exists(path) and path.endswith('/data'):
            # FIXME: Handle grits-like query with /data appended to path
            # stupid grits
            if exists(path[:-5]):
                path = path[:-5]

        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None

        if self.range_from is None:
            self.send_response(200)
        else:
            self.send_response(206)

        self.send_header("Content-type", ctype)
        fs = fstat(f.fileno())
        file_size = fs.st_size
        if self.range_from is not None:
            if self.range_to is None or self.range_to >= file_size:
                self.range_to = file_size-1
            self.send_header("Content-Range",
                             "bytes %d-%d/%d" % (self.range_from,
                                                 self.range_to,
                                                 file_size))
            # Add 1 because ranges are inclusive
            self.send_header("Content-Length",
                             (1 + self.range_to - self.range_from))
        else:
            self.send_header("Content-Length", str(file_size))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f, file_size

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (quote(linkname), cgi.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """ Override to handle redirects.
        """
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = normpath(unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = self.serve_path
        for word in words:
            drive, word = splitdrive(word)
            head, word = split(word)
            if word in (curdir, pardir): continue
            path = join(path, word)
        return path

    # Private interface ######################################################

    def _get_range_header(self):
        """ Returns request Range start and end if specified.
        If Range header is not specified returns (None, None)
        """
        range_header = self.headers.get("Range")
        if range_header is None:
            return (None, None)
        if not range_header.startswith("bytes="):
            return (None, None)
        regex = re.compile(r"^bytes=(\d+)\-(\d+)?")
        rangething = regex.search(range_header)
        if rangething:
            from_val = int(rangething.group(1))
            if rangething.group(2) is not None:
                return (from_val, int(rangething.group(2)))
            else:
                return (from_val, None)
        else:
            return (None, None)


def get_server(port=8000, next_attempts=0, serve_path=None):
    Handler = RequestHandler
    if serve_path:
        Handler.serve_path = serve_path
    while next_attempts >= 0:
        try:
            httpd = ThreadingHTTPServer(("", port), Handler)
            return httpd
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                next_attempts -= 1
                port += 1
            else:
                raise

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    PORT = 8000
    if len(args)>0:
        PORT = int(args[-1])
    serve_path = DATA_DIR
    if len(args) > 1:
        serve_path = abspath(args[-2])

    httpd = get_server(port=PORT, serve_path=serve_path)

    httpd.serve_forever()

if __name__ == "__main__" :
    main()
