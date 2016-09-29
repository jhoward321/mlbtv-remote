# MLBtv Remote

This is a custom API front end for the popular [mlbviewer project](https://sourceforge.net/projects/mlbviewer/). This project is still a work in progress and this README will be updated as I add more functionality. This project was meant to allow me to watch MLBtv on my raspberry pi without having to manually select the game on the device. 


Currently the API will provide MLB game schedules for different dates and teams. It will start specified games (MLB.tv account required). I still am adding features and cleaning up bugs, and the code will be cleaned up as I finish features. Future plans include a remote command line interface to start mlbviewer on a separate machine. Right now the API must be used through HTTP requests. The project will use omxplayer for hardware acceleration if run on a raspberry pi, and will use mplayer if used on a typical linux machine.

##How to Setup

This frontend requires Python, the [mlbviewer project](https://sourceforge.net/p/mlbviewer/code/HEAD/tree/trunk/), and a few python libraries.

* First download and setup the mlbviewer project:
```
$ svn checkout svn://svn.code.sf.net/p/mlbviewer/code/trunk mlbviewer-code
```
* Install required Python dependencies:
```
$ sudo pip install flask flask_restful marshmallow
```
* With server.py in the same folder as the MLBviewer folder:
```
$ python server.py
```
The server is now running, and is ready to accept commands.

## Usage

After following the setup steps, the server is ready to accept http requests. Below I've listed some of the most useful commands.

#### Get current day's game schedule:
```
$ curl -v -G 127.0.0.1:5000/
```
#### Get specific date's game schedule:
```
$ curl -v -G 127.0.0.1:5000/schedule -d 'date=2016-08-11'
```
#### Get game info for specific team on specific date:
```
$ curl -v -G 127.0.0.1:5000/schedule/[team_code] -d 'date=2016-08-11'
```
#### Play todays game for [team] if available:
```
$ curl -v -X PUT 127.0.0.1:5000/play/[team]
```
#### Play game for [team] on specific date:
```
$ curl -v -X PUT 127.0.0.1:5000/play/[team] -d date='2016-09-05'
```