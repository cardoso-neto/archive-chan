# archive-chan
> Download 4chan threads and save the images/videos

Download entire threads directly from 4chan's API.
All while preserving the format of the discussion, as well as all media (videos, gifs, or images) that may have been posted.
Allowing you to browse it offline forever.

Each thread is then rendered as an html file in a similar layout to 4chan albeit a lot simplified (any front-end engineers feel like improving it? All help is welcome).

Note:
Media is not unnecessarily redownloaded, so you will not waste bandwidth and time.
However, if a mod deletes a post and you rerun archive-chan on that thread, you will lose that post, as I haven't implemented a solution for that yet.

## Installation

`pip install git+https://github.com/cardoso-neto/archive-chan.git@master`

and you can also run `pip install --upgrade archive-chan` from time to time to receive updates.

Note:
`archive-chan` only runs on Python 3.7.x for now.
I use [miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) to manage my many python versions.
After installing miniconda, you can create an env with:

`conda create --name chan python=3.7`

Activate it with `conda activate chan` and then install archive-chan with the pip command above.

## Usage

### Archive 4chan threads or catalogs

To archive one or multiple threads of your choosing pass in the thread url or a text file of thread urls each on a new line to `archive-chan`.

This is the help output:

```bash
$ archive-chan --help
usage: archive-chan [-h] [-a] [-ao] [-p] [--path PATH] [--posts POSTS]
                    [-r RETRIES] [--skip_renders] [--text_only] [-v]
                    thread

Archive 4chan threads

positional arguments:
  thread                Link to the 4chan thread or the name of the board.

optional arguments:
  -h, --help            show this help message and exit
  -a, --archived        Download threads from the /board/archive/ as well.
  -ao, --archived_only  Download threads from the /board/archive/ INSTEAD.
  -p, --preserve_media  Save images and video files locally.
  --path PATH           Path to folder where the threads should be saved.
  --posts POSTS         Number of posts to download
  --skip_renders        Do not render any threads.
  --text_only           Download only HTMLs or JSONs.
  -v, --verbose         Verbose logging to stdout.
```

### Examples

#### download every post in a thread and save all the media uploaded

```bash
archive-chan http://boards.4chan.org/p/thread/3434289/ect-edit-challenge-thread -p -v
```

Archive all threads from a board to a specific path, e.g., every every active thread as well as every archived thread from /g/ to a `./downloads` folder (if it doesn't exist, it will be created):

```bash
$ archive-chan g --archived --preserve_media --verbose --path ./downloads/

Dump to 'downloads/g/79745590/thread.json' ...
    Complete! Elapse 0.022107 sec.

Dump to 'downloads/g/76759434/thread.json' ...
    Complete! Elapse 0.002117 sec.

Dump to 'downloads/g/79748257/thread.json' ...
    Complete! Elapse 0.004685 sec.
...
```

#### batch download handpicked threads

Create a `.txt` file somewhere and paste a thread URL on each line.
Then feed it to the URL argument as such:

`archive-chan threads.txt -p -v`

### Tips

* Don't be afraid to ctrl+c and run it again.
Everything is idempotent and it'll resume from where it left-off.
* If it looks stuck, it's probably stuck.
Just rerun it.
No, I don't know why it hangs so often.

## Beta

This software is in its early stages.
Report bugs and contribute if possible.

Come chat with me, other devs, and other users on [gitter.im/archive-chan](https://gitter.im/archive-chan/).

## Dev build

`git clone git@github.com:cardoso-neto/archive-chan.git`

`pip install -e ./`
