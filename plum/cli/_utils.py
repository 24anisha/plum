from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def multiprocess(func, data, num_processes=None):
    """Run a function on multiple processes."""
    if num_processes is None:
        # Determine the number of processes.
        # We want to use as many processes as necessary, but not more than 60.
        # Python's multiprocessing library has innate problems on Windows.
        # We also leave 1 thread for OS processes.
        num_processes = min(cpu_count() - 1, len(data), 60)

    with Pool(processes=num_processes) as pool:
        results = list(tqdm(pool.imap_unordered(func, data), total=len(data)))

    return results
