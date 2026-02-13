package anonymous

import io.github.oshai.kotlinlogging.KotlinLogging
import java.io.File
import java.io.IOException
import java.lang.instrument.Instrumentation
import java.util.Properties

import org.apache.log4j.ConsoleAppender
import org.apache.log4j.Level
import org.apache.log4j.Logger
import org.apache.log4j.PatternLayout
import org.apache.log4j.RollingFileAppender

@Suppress("unused")
object DetectAgent {
    internal const val D4J_FILE = "defects4j.build.properties"
    private const val D4J_CLASSES = "d4j.classes"
    private const val D4J_METHODS = "d4j.methons"
    private val logger = KotlinLogging.logger {}

    /**
     * 在主线程启动之前进行处理
     *
     * @param agentArgs       代理请求参数
     * @param instrumentation 插桩
     */
    @JvmStatic
    fun premain(agentArgs: String?, instrumentation: Instrumentation) {

        println("agentArgs="+agentArgs)

        val command = System.getProperty("sun.java.command")
        if (command != null && "defects4j.build.xml" in command
            && !command.endsWith("run.dev.tests")
        ) {
            return
        }
        val baseDirStr = System.getProperty("user.dir") ?: return
        val baseDir = File(baseDirStr)
        val properties = Properties()
        try {
            properties.load(File(baseDir, D4J_FILE).reader())
        } catch (e: IOException) {
            logger.error { e.stackTraceToString() }
            logger.info { "Error when reading file: $D4J_FILE! Skip." }
        }
        val args: Properties =
            try {
                if (agentArgs != null) {
                    Properties().apply {
                        load(File(agentArgs).reader())
                    }
                } else {
                    Properties()
                }
            } catch (e: IOException) {
                logger.error { e.stackTraceToString() }
                logger.info { "Error when reading file: $agentArgs! Skip." }
                Properties()
            }


        // 配置 log4j
        val logFilePath = args.getProperty("log.file.path", "bugDetect.log") // 默认值 bugDetect.log
        val oriLogFilePath = args.getProperty("ori.log.file.path", "bugDetectOri.log") // 默认值 bugDetectOri.log

        // 配置 console appender
        val consoleAppender = ConsoleAppender()
        consoleAppender.layout = PatternLayout("%m%n")
        consoleAppender.threshold = Level.DEBUG
        consoleAppender.activateOptions() // 激活配置

        // 配置 file appender（small logger）
        val fileAppender = RollingFileAppender()
        fileAppender.file = logFilePath
        fileAppender.setMaxFileSize("5KB")  // Use setMaxFileSize with a String value
        fileAppender.layout = PatternLayout("%m%n")
        fileAppender.threshold = Level.INFO
        fileAppender.activateOptions() // Activate configuration

        // 配置 oriFile appender（ori logger）
        val oriFileAppender = RollingFileAppender()
        oriFileAppender.file = oriLogFilePath
        oriFileAppender.setMaxFileSize("5KB")  // Use setMaxFileSize with a String value
        oriFileAppender.layout = PatternLayout("%m%n")
        oriFileAppender.threshold = Level.INFO
        oriFileAppender.activateOptions() // Activate configuration

        // 配置 logger
        val rootLogger = Logger.getRootLogger()
        rootLogger.level = Level.DEBUG
        rootLogger.addAppender(consoleAppender)

        val smallLogger = Logger.getLogger("anonymous.logger.small")
        smallLogger.level = Level.INFO
        smallLogger.addAppender(fileAppender)
        smallLogger.additivity = false

        val oriLogger = Logger.getLogger("anonymous.logger.ori")
        oriLogger.level = Level.INFO
        oriLogger.addAppender(oriFileAppender)
        oriLogger.additivity = false

        // 继续原有逻辑
        val classes = properties.getProperty(D4J_CLASSES, "").split(",").toSet()
        val methods = properties.getProperty(D4J_METHODS, "").split(",").toSet()

        println("classes="+classes)
        println("methods="+methods)
        instrumentation.addTransformer(DetectTransformer(classes, methods, args), true)
    }
}