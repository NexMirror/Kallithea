.. _performance:

================================
Optimizing Kallithea performance
================================

When serving a large amount of big repositories, Kallithea can start
performing slower than expected. Because of the demanding nature of handling large
amounts of data from version control systems, here are some tips on how to get
the best performance.

Follow these few steps to improve performance of Kallithea system.

1.  Kallithea is often I/O bound, and hence a fast disk (SSD/SAN) is
    usually more important than a fast CPU.

2. Increase cache

    Tweak beaker cache settings in the ini file. The actual effect of that
    is questionable.

3. Switch from SQLite to PostgreSQL or MySQL

    SQLite is a good option when having a small load on the system. But due to
    locking issues with SQLite, it is not recommended to use it for larger
    deployments. Switching to MySQL or PostgreSQL will result in an immediate
    performance increase. A tool like SQLAlchemyGrate_ can be used for
    migrating to another database platform.

4. Scale Kallithea horizontally

    Scaling horizontally can give huge performance benefits when dealing with
    large amounts of traffic (many users, CI servers, etc.). Kallithea can be
    scaled horizontally on one (recommended) or multiple machines. In order
    to scale horizontally you need to do the following:

    - Each instance's ``data`` storage needs to be configured to be stored on a
      shared disk storage, preferably together with repositories. This ``data``
      dir contains template caches, sessions, whoosh index and is used for
      task locking (so it is safe across multiple instances). Set the
      ``cache_dir``, ``index_dir``, ``beaker.cache.data_dir``, ``beaker.cache.lock_dir``
      variables in each .ini file to a shared location across Kallithea instances
    - If celery is used each instance should run a separate Celery instance, but
      the message broker should be common to all of them (e.g.,  one
      shared RabbitMQ server)
    - Load balance using round robin or IP hash, recommended is writing LB rules
      that will separate regular user traffic from automated processes like CI
      servers or build bots.

5. Serve static files directly from the web server

With the default ``static_files`` ini setting, the Kallithea WSGI application
will take care of serving the static files found in ``kallithea/public`` from
the root of the application URL. While doing that, it will currently also
apply buffering and compression of all the responses it is serving.

The actual serving of the static files is unlikely to be a problem in a
Kallithea setup. The buffering of responses is more likely to be a problem;
large responses (clones or pulls) will have to be fully processed and spooled
to disk or memory before the client will see any response.

To serve static files from the web server, use something like this Apache config
snippet::

        Alias /images/ /srv/kallithea/kallithea/kallithea/public/images/
        Alias /css/ /srv/kallithea/kallithea/kallithea/public/css/
        Alias /js/ /srv/kallithea/kallithea/kallithea/public/js/
        Alias /codemirror/ /srv/kallithea/kallithea/kallithea/public/codemirror/
        Alias /fontello/ /srv/kallithea/kallithea/kallithea/public/fontello/

Then disable serving of static files in the ``.ini`` ``app:main`` section::

        static_files = false

If using Kallithea installed as a package, you should be able to find the files
under site-packages/kallithea, either in your Python installation or in your
virtualenv. When upgrading, make sure to update the web server configuration
too if necessary.


.. _SQLAlchemyGrate: https://github.com/shazow/sqlalchemygrate
