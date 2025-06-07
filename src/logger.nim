import logging

try:
  var logger = newFileLogger("app.log", fmtStr = "[$datetime] [$levelname] ")
  addHandler(logger)
except IOError:
  stderr.writeLine("无法创建日志文件！")
  quit(1)
