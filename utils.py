import threading, queue, functools
from collections.abc import Generator
from contextlib import closing

SENTINEL = StopIteration


# source: https://gist.github.com/monkeytruffle/36a57792bad4f0c507c6be8111526ec6#file-threaded_generator-py-L127
class ThreadedGenerator(Generator, closing):
    """
    Creates a generator that asynchronously produces a queue of results from any iterable object in
    a new thread, and yields the results consumed from that queue within the current thread.
    The interface is that of a generator - including __iter__, __next__, send, throw and close
    methods - and also that of a context manager: i.e. it has __enter__ and __exit__ methods.
    (Note: of these methods mentioned, all but 'send' and 'throw' are inherited).
    The constructor accepts the arguments 'iterable' and, optionally, 'maxq'
    'iterable' is the object forming the source of the data ultimately yielded. It can be any
    iterable object, though typically will be an I/O bound iterator or generator (but not a
    generator function: see ThreadedGenFunc).
    'maxq' defines the maximum size to which the internal queue is allowed to grow, with 0 (the
    default) representing an unlimited queue. It is important to specify a limit for iterators
    producing a very large or unlimited number of values.
    The 'send' and 'throw' methods are required internally to implement '__next__' and 'close', but
    are not intended to be called externally (other than perhaps for testing and debugging - or, a
    subclass could override '_dequeue' to incorporate logic responsive to send and throw calls.)
    The 'close' method is only needed when fewer results are consumed than are produced from the
    iterable object passed in (unless this is due to an exception: that situation is resolved
    without requiring 'close'). The method not only closes the generator (so that no further
    iteration is permitted) but also, importantly, allows the thread to terminate, thus avoiding
    potential resource leakage.
    To make closing more convenient, the class can be used as a context manager:
    Example:
    ```
    with ThreadedGenerator(it, maxq=1000) as tg:
        for i in tg:
            # do something with yielded results
    # generator will now close, along with its internal thread
    ```
    """

    def __init__(self, iterable, maxq=0):
        closing.__init__(self, self)
        self._queue = queue.Queue(maxq)
        self._producer = threading.Thread(target=self._enqueue, args=(iterable,), daemon=True)
        self._consumer = self._dequeue()
        self._thread_kill, self._thread_err = False, None
        self._producer.start()

    def _enqueue(self, iterable):
        try:
            for _ in map(self._queue.put, iterable):
                if self._thread_kill:
                    break
        except Exception as err:
            self._thread_err = err
            print("%r in thread", err)
        finally:
            self._queue.put(SENTINEL)
            print("Sentinel put; thread should now exit")

    def _dequeue(self):
        try:
            for i in iter(self._queue.get, SENTINEL):
                yield i
        finally:
            self._force_join()
            if self._thread_err is not None:
                raise RuntimeError(f"Error in thread {self._producer}") from self._thread_err

    def _force_join(self):
        self._thread_kill = True
        # remove _queue's maxsize so neither put call in _enqueue blocks, ensuring it returns
        with self._queue.mutex:
            self._queue.maxsize = float("inf")
            self._queue.not_full.notify()

    def send(self, value):  # implements inherited __next__ method
        return self._consumer.send(value)

    def throw(self, typ, val=None, tb=None):  # implements inherited close method
        print("throw called with arg %s", typ)
        self._consumer.throw(typ)  # (typ, val, tb) signature of throw() deprecated


class ThreadedGenFunc:
    """
    A decorator class for generator functions. A decorated generator function will, when called,
    result in a ThreadedGenerator object. The decorator will work both on functions and on methods.
    The decorator should use the ThreadedGenFunc class, not an instance. Specifying
    ThreadedGenerator's optional maxq argument is achieved by means of ThreadedGenFunc's
    classmethod 'with_maxq'.
    For example, to get a ThreadedGenerator object with an unlimted internal queue, the decorator
    @ThreadedGenFunc would be appropriate but, otherwise, @ThreadedGenFunc.with_maxq(1000) could be
    used (for a queue size of 1000). Alternatively, set a variable to the result of the 'with_maxq'
    call and use that variable as the decorator: MyThrGenFunc = ThreadedGenFunc.with_maxq(1000),
    then decorate with @MyThrGenFunc.
    """

    def __init__(self, genfunc):
        self._genfunc = genfunc
        self.maxq = 0

    @classmethod
    def with_maxq(cls, maxq):
        def decorator(genfunc):
            thr_genfunc = cls(genfunc)
            thr_genfunc.maxq = maxq
            return thr_genfunc

        return decorator

    def __get__(self, instance, owner=None):
        # for when the generator function is a method
        return functools.partial(self.__call__, instance)

    def __call__(self, *args, **kwargs):
        generator = self._genfunc(*args, **kwargs)
        return ThreadedGenerator(generator, self.maxq)
