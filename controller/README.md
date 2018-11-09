## OtterTune Controller
The controller is responsible for collecting database metrics and knobs information during an experiment.</br>
#### Usage:
To build the project, run `gradle build`.</br>
To run the controller, you need to provide a configuration file and provide command line arguments (command line arguments are optional). Then run `gradle run`.

 * Command line arguments:
   * time (flag : `-t`) </br>
     The duration of the experiment in `seconds`. The default time is set to 300 seconds.
   * configuration file path (flag : `-c`) </br>
     The path of the input configuration file (required). Sample config files are under the directory `config`.
 
