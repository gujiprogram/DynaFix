@file:Suppress("unused")

package anonymous

import anonymous.logger.ori.OriDebugLoggerHelper
import anonymous.logger.small.SmallDebugLoggerHelper
import com.google.gson.*
import java.io.File
import java.lang.reflect.Type
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CopyOnWriteArrayList
import kotlin.collections.*

object DetectMonitor {

    private const val VAR_JSON_MAX_LENGTH = 512
    private const val VAR_JSON_MAX_BRACE = 128
    private const val VAR_ARRAY_MAX_LENGTH = 32
    private val notChangedVarRecorder = ConcurrentHashMap<String, ConcurrentHashMap<String, String>>()
    private val branchInfoMap = ConcurrentHashMap<String, CopyOnWriteArrayList<String>>()
    private val loopInfoMap = ConcurrentHashMap<String, CopyOnWriteArrayList<String>>()

    private val normalGson: Gson = GsonBuilder().create()

    internal object ClassJsonSerializer: JsonSerializer<Class<*>?> {
        override fun serialize(p0: Class<*>?, p1: Type?, p2: JsonSerializationContext?): JsonElement {
            return JsonPrimitive(p0.toString())
        }
    }

    internal object ArrayJsonSerializer: JsonSerializer<Array<*>?> {
        override fun serialize(p0: Array<*>?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object CollectionJsonSerializer: JsonSerializer<Collection<*>?> {
        override fun serialize(p0: Collection<*>?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.take(VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object ByteArrayJsonSerializer: JsonSerializer<ByteArray?> {
        override fun serialize(p0: ByteArray?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object CharArrayJsonSerializer: JsonSerializer<CharArray?> {
        override fun serialize(p0: CharArray?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object IntArrayJsonSerializer: JsonSerializer<IntArray?> {
        override fun serialize(p0: IntArray?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object ShortArrayJsonSerializer: JsonSerializer<ShortArray?> {
        override fun serialize(p0: ShortArray?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object FloatArrayJsonSerializer: JsonSerializer<FloatArray?> {
        override fun serialize(p0: FloatArray?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object DoubleArrayJsonSerializer: JsonSerializer<DoubleArray?> {
        override fun serialize(p0: DoubleArray?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    internal object BooleanArrayJsonSerializer: JsonSerializer<BooleanArray?> {
        override fun serialize(p0: BooleanArray?, p1: Type?, p2: JsonSerializationContext): JsonElement {
            if (p0 == null) return JsonNull.INSTANCE
            if (p0.size <= VAR_ARRAY_MAX_LENGTH) return normalGson.toJsonTree(p0)
            val array = p0.copyOfRange(0, VAR_ARRAY_MAX_LENGTH)
            val result = normalGson.toJsonTree(array).asJsonArray
            result.add("...")
            return result
        }
    }

    @JvmStatic
    val mayErrorGson: Gson = GsonBuilder()
        .registerTypeAdapter(Class::class.java, ClassJsonSerializer)
        .registerTypeAdapter(Array::class.java, ArrayJsonSerializer)
        .registerTypeAdapter(Collection::class.java, CollectionJsonSerializer)
        .registerTypeAdapter(ByteArray::class.java, ByteArrayJsonSerializer)
        .registerTypeAdapter(CharArray::class.java, CharArrayJsonSerializer)
        .registerTypeAdapter(IntArray::class.java, IntArrayJsonSerializer)
        .registerTypeAdapter(ShortArray::class.java, ShortArrayJsonSerializer)
        .registerTypeAdapter(FloatArray::class.java, FloatArrayJsonSerializer)
        .registerTypeAdapter(DoubleArray::class.java, DoubleArrayJsonSerializer)
        .registerTypeAdapter(BooleanArray::class.java, BooleanArrayJsonSerializer)
        .create()

    internal object AllObjectSerializer: JsonSerializer<Any> {
        override fun serialize(p0: Any?, p1: Type?, p2: JsonSerializationContext?): JsonElement {
            return try {
                mayErrorGson.toJsonTree(p0, p1)
            } catch (e: Throwable) {
                JsonPrimitive(p0.toString())
            } catch (e: StackOverflowError) {
                JsonPrimitive(p0.toString())
            }
        }
    }

    @JvmStatic
    val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Class::class.java, ClassJsonSerializer)
        .registerTypeHierarchyAdapter(Any::class.java, AllObjectSerializer)
        .addReflectionAccessFilter(ReflectionAccessFilter.BLOCK_INACCESSIBLE_JAVA)
        .create()

    @JvmStatic
    fun monitorEnterMethod(name: String) {
        // Clear local variables and control flow info when entering a method
        notChangedVarRecorder.computeIfAbsent(name) { ConcurrentHashMap() }
        branchInfoMap.computeIfAbsent(name) { CopyOnWriteArrayList() }
        loopInfoMap.computeIfAbsent(name) { CopyOnWriteArrayList() }
    }

    @JvmStatic
    fun monitorLocalVar(line: Int, vars: HashMap<String, Any?>, relevant: Boolean) {
        if (vars.isEmpty()) return
        println("Calling monitorLocalVar with line: $line, variables: $vars, relevant: $relevant")


        val stack = Thread.currentThread().stackTrace
        val className = stack[2].className
        val methodName = stack[2].methodName
        val methodFullName = "$className::$methodName"


        val oriStr = gson.toJson(vars)
        println("oriStr="+oriStr)
        println("vars="+vars)
        if (oriStr != "{}") {
            OriDebugLoggerHelper.logger.info { "$className:$methodName:$line->[Local Variables] $oriStr" }
        }

        if (relevant) return
        if (!notChangedVarRecorder.containsKey(methodFullName)) {
            notChangedVarRecorder[methodFullName] = ConcurrentHashMap()
        }
        val methodRecord = notChangedVarRecorder[methodFullName]!!
        val strMap = hashMapOf<String, Any?>()
        for ((str, value) in vars) {
            val valueStr = gson.toJson(value)
            if (valueStr.length > VAR_JSON_MAX_LENGTH || valueStr.count { it == '{' } > VAR_JSON_MAX_BRACE) {
                continue
            }
            if (methodRecord[str] == valueStr) {
                continue
            }
            strMap[str] = value
            methodRecord[str] = valueStr
        }
        if (strMap.isEmpty()) return
        val varsStr = gson.toJson(strMap)
        if (varsStr != "{}") {
            SmallDebugLoggerHelper.logger.info { "$className:$methodName:$line->[Local Variables] $varsStr" }
        }
    }

    @JvmStatic
    fun monitorBranch(className: String, methodName: String, line: Int, condition: String, executed: Boolean) {
        val methodFullName = "$className::$methodName"
        branchInfoMap.computeIfAbsent(methodFullName) { CopyOnWriteArrayList() }
        val branchStr = "Branch Info: Line: $line, Condition: $condition, Executed: $executed"
        branchInfoMap[methodFullName]!!.add(branchStr)
        SmallDebugLoggerHelper.logger.info { "$className:$methodName:$line->[Control Flow] $branchStr" }
    }

    @JvmStatic
    fun monitorLoop(className: String, methodName: String, line: Int, description: String) {
        val methodFullName = "$className::$methodName"
        loopInfoMap.computeIfAbsent(methodFullName) { CopyOnWriteArrayList() }
        val loopStr = "Loop Info: Line: $line, Description: $description"
        loopInfoMap[methodFullName]!!.add(loopStr)
        SmallDebugLoggerHelper.logger.info { "$className:$methodName:$line->[Control Flow] $loopStr" }
    }

    @JvmStatic
    fun monitorMethodCall(
        className: String,
        methodName: String,
        line: Int,
        calledClass: String,
        calledMethod: String
    ) {
        val callStr = "Call Stack: ${className}.${methodName}:$line -> ${calledClass.replace('/', '.')}.$calledMethod"
        SmallDebugLoggerHelper.logger.info { "$className:$methodName:$line->[Method Call] $callStr" }
    }
}