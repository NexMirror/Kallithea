.. _performance:

================================
Optimizing Kallithea performance
================================

When serving a large amount of big repositories, Kallithea can start
performing slower than expected. Because of the demanding nature of handling large
amounts of data from version control systems, here are some tips on how to get
the best performance.

* Kallithea is often I/O bound, and hence a fast disk (SSD/SAN) is
  usually more important than a fast CPU.

* Sluggish loading of the front page can easily be fixed by grouping repositories or by
  increasing cache size (see below). This includes using the lightweight dashboard
  option and ``vcs_full_cache`` setting in .ini file.

Follow these few steps to improve performance of Kallithea system.

1. Increase cache

    Tweak beaker cache settings in the ini file. The actual effect of that
    is questionable.

2. Switch from SQLite to PostgreSQL or MySQL

    SQLite is a good option when having a small load on the system. But due to
    locking issues with SQLite, it is not recommended to use it for larger
    deployments. Switching to MySQL or PostgreSQL will result in an immediate
    performance increase. A tool like SQLAlchemyGrate_ can be used for
    migrating to another database platform.

3. Scale Kallithea horizontally

    Scaling horizontally can give huge performance benefits when dealing with
    large amounts of traffic (many users, CI servers, etc.). Kallithea can be
    scaled horizontally on one (recommended) or multiple machines.

    It is generally possible to run WSGI applications multithreaded, so that
    several HTTP requests are served from the same Python process at once. That
    can in principle give better utilization of internal caches and less
    process overhead.

    One danger of running multithreaded is that program execution becomes much
    more complex; programs must be written to consider all combinations of
    events and problems might depend on timing and be impossible to reproduce.

    Kallithea can't promise to be thread-safe, just like the embedded Mercurial
    backend doesn't make any strong promises when used as Kallithea uses it.
    Instead, we recommend scaling by using multiple server processes.

    Web servers with multiple worker processes (such as ``mod_wsgi`` with the
    ``WSGIDaemonProcess`` ``processes`` parameter) will work out of the box.

    In order to scale horizontally on multiple machines, you need to do the
    following:

    - Each instance needs its own .ini file and unique ``instance_id`` set.
    - Each instance's ``data`` storage needs to be configured to be stored on a
      shared disk storage, preferably together with repositories. This ``data``
      dir contains template caches, sessions, whoosh index and is used for
      task locking (so it is safe across multiple instances). Set the
      ``cache_dir``, ``index_dir``, ``beaker.cache.data_dir``, ``beaker.cache.lock_dir``
      variables in each .ini file to a shared location across Kallithea instances
    - If using several Celery instances,
      the message broker should be common to all of them (e.g.,  one
      shared RabbitMQ server)
    - Load balance using round robin or IP hash, recommended is writing LB rules
      that will separate regular user traffic from automated processes like CI
      servers or build bots.


.. _SQLAlchemyGrate: https://github.com/shazow/sqlalchemygrate
