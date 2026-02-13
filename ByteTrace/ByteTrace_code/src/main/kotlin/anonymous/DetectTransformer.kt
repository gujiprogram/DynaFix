package anonymous

import anonymous.DetectAgent.D4J_FILE
import anonymous.utils.boxIfNeed
import anonymous.utils.isWriteLocalVar
import anonymous.utils.loadVar
import io.github.oshai.kotlinlogging.KotlinLogging
import org.objectweb.asm.ClassReader
import org.objectweb.asm.ClassWriter
import org.objectweb.asm.Opcodes.*
import org.objectweb.asm.Type
import org.objectweb.asm.commons.AdviceAdapter
import org.objectweb.asm.tree.*
import java.lang.instrument.ClassFileTransformer
import java.security.ProtectionDomain
import org.objectweb.asm.Opcodes
import java.util.*
import kotlin.collections.HashMap
import kotlin.collections.HashSet


class DetectTransformer(
    classes: Set<String>,
    /**
     * methods here only used by transform d4j test classes
     */
    methods: Set<String>,
    args: Properties
): ClassFileTransformer {

    private val classes: HashSet<String> = HashSet()
    private val methods: HashSet<String> = HashSet()

    /** Monitor only changed variables or not.
     * Note that all variables will be monitored when they come out for the first time.
     */
    private val changedLocalVarsOnly = args.getProperty(KEY_CHANGED_LOCAL_VARS_ONLY, "false").toBoolean()

    init {
        if (!args.getProperty(KEY_ARGS_USE_SPECIFIED).toBoolean()) {
            this.classes.addAll(classes)
            for (methodName in methods) {
                this.classes.add(methodName.split("::")[0])
            }
        } else {
            val specifiedMethods = args.getProperty(KEY_ARGS_METHODS, "").split(",")
            this.methods.addAll(specifiedMethods)
            val specifiedClasses = args.getProperty(KEY_ARGS_CLASSES, "").split(",")
            this.classes.addAll(specifiedClasses)
            for (methodName in specifiedMethods) {
                this.classes.add(methodName.split("::")[0])
            }
            val addingMethods = HashSet<String>()
            for (method in this.methods) {
                if (method.isEmpty()) continue
                val clazzAndMethodName = method.split("::")
                val clazzName = clazzAndMethodName[0]
                val methodName = clazzAndMethodName[1]
                if (clazzName.endsWith(methodName)) {
                    addingMethods.add("${clazzName}::<init>")
                }
            }
            this.methods.addAll(addingMethods)
            this.classes.remove("")
            this.methods.remove("")
            if (this.classes.isEmpty() && this.methods.isEmpty()) {
                // when baseline location is not available, use relevant ones.
                this.classes.addAll(classes)
            }
            println("this.methods="+this.methods)
            println("this.classes="+this.classes)
        }
        this.classes.remove("")
        this.methods.remove("")
        // hard code to avoid print exception classes
        this.classes.removeIf { "Exception" in it }
    }

    companion object {
        private val logger = KotlinLogging.logger {}
        private const val KEY_CHANGED_LOCAL_VARS_ONLY = "changedLocalVarsOnly"

        /**
         * Use specified but not classes in [D4J_FILE]
         */
        private const val KEY_ARGS_USE_SPECIFIED = "args.use.specified"
        private const val KEY_ARGS_CLASSES = "args.classes"
        private const val KEY_ARGS_METHODS = "args.methods"
        val classNameWhiteList = listOf(
            DetectAgent::class.java,
            DetectMonitor::class.java,
            DetectTransformer::class.java,
            Companion::class.java,
            DetectMonitor.ClassJsonSerializer::class.java,
            DetectMonitor.AllObjectSerializer::class.java,
        ).map(Type::getInternalName).toHashSet()
    }


    override fun transform(
        loader: ClassLoader?,
        className: String?,
        classBeingRedefined: Class<*>?,
        protectionDomain: ProtectionDomain?,
        classfileBuffer: ByteArray?
    ): ByteArray? {
        val classLoader = loader ?: ClassLoader.getSystemClassLoader()

        if (className == null || className in classNameWhiteList) {
            return null
        }
        try {
            val classReader = ClassReader(
                classLoader.getResourceAsStream(className.replace(".", "/") + ".class")
            )
            val classWriter = ClassWriter(ClassWriter.COMPUTE_FRAMES)
            val classNode = ClassNode(ASM9)
            classReader.accept(classNode, ClassReader.EXPAND_FRAMES)
            transformClass(classNode)
            classNode.accept(classWriter)
            return classWriter.toByteArray()
        } catch (e: Exception) {
            logger.error { e.stackTraceToString() }
        }
        return classfileBuffer
    }

    private fun transformClass(classNode: ClassNode) {
        for (method in classNode.methods) {
            try {
                val fullMethodName = "${classNode.name.replace("/", ".")}::${method.name}"
                if (fullMethodName in methods) {
                    println("Method name: ${method.name}")
                    println("Method descriptor: ${method.desc}")
                    println("Method code: ${method.instructions}")
                    println("classNode.name="+classNode.name)
                    transformMethod(method, classNode.name)
                }
            } catch (e: Throwable) {
                e.printStackTrace()
            }
        }
    }

    private fun transformMethod(methodNode: MethodNode, owner: String) {
        val fullMethodName = "${owner.replace("/", ".")}::${methodNode.name}"
        println("Start transforming method: $fullMethodName")  // 调试信息: 方法开始处理
        val relevant = if (methods.isNotEmpty() && fullMethodName !in methods) {
            true
        } else {
            false
        }
        println("Method relevance: $relevant")  // 调试信息: 方法是否相关

        if (methodNode.name == "<clinit>" || methodNode.localVariables == null) {
            println("Skipping method: ${methodNode.name} (clinit or no local variables)")  // 调试信息: 跳过clinit或没有局部变量的方法
            return
        }

        if (!relevant && fullMethodName in methods) {
            println("Analyzing control flow for method: $fullMethodName")  // 调试信息: 分析控制流
            analyzeControlFlow(methodNode, owner)
            analyzeMethodCalls(methodNode, owner)

        }

        val notFirstTimeVars = hashSetOf<LocalVariableNode>()
        val availableVars = hashMapOf<Int, LocalVariableNode>()
        val wroteOrFirstVisitVars = hashSetOf<LocalVariableNode>()
        val startVarMap = hashMapOf<LabelNode, HashMap<Int, LocalVariableNode>>()
        val endVarMap = hashMapOf<LabelNode, HashMap<Int, LocalVariableNode>>()

        // 跟踪局部变量的添加
        for (localVar in methodNode.localVariables) {
            if (localVar.start !in startVarMap) {
                startVarMap[localVar.start] = HashMap()
            }
            if (localVar.end !in endVarMap) {
                endVarMap[localVar.end] = HashMap()
            }
            startVarMap[localVar.start]!![localVar.index] = localVar
            endVarMap[localVar.end]!![localVar.index] = localVar
            println("Local variable added: ${localVar.name} at index ${localVar.index}")  // 调试信息: 添加局部变量
        }

        val modifications = mutableListOf<Pair<AbstractInsnNode, InsnList>>()
        var i = 0
        while (i < methodNode.instructions.size()) {
            val inst = methodNode.instructions[i]
            println("Processing instruction at index $i: $inst")  // 调试信息: 当前处理的指令

            if (inst is LabelNode) {
                if (inst in startVarMap) {
                    val varNodes = startVarMap[inst]!!
                    availableVars.putAll(varNodes)
                    println("Updated availableVars with start variables at label $inst")  // 调试信息: 更新可用变量
                }
                if (inst in endVarMap) {
                    val varNodes = endVarMap[inst]!!
                    for ((index, _) in varNodes) {
                        availableVars.remove(index)
                        println("Removed variable from availableVars at label $inst")  // 调试信息: 移除变量
                    }
                }
            }

            if (changedLocalVarsOnly) {
                if (inst is VarInsnNode) {
                    if (availableVars.containsKey(inst.`var`)) {
                        val localVar = availableVars[inst.`var`]!!
                        if (inst.isWriteLocalVar()) {
                            wroteOrFirstVisitVars.add(localVar)
                            println("Marked localVar as written: ${localVar.name}")  // 调试信息: 标记局部变量为已写入
                        }
                    }
                }
            }

            if (inst is LineNumberNode) {
                if (availableVars.isEmpty()) {
                    i++
                    continue
                }
                val insnList = if (changedLocalVarsOnly) {
                    for ((_, varNode) in availableVars) {
                        if (varNode !in notFirstTimeVars) {
                            notFirstTimeVars.add(varNode)
                            wroteOrFirstVisitVars.add(varNode)
                            println("Visited Variables: ${wroteOrFirstVisitVars.map { it.name }}")
                            println("Added to notFirstTimeVars: ${varNode.name}")  // 调试信息: 添加到未访问过的变量集合
                        }
                    }
                    generateMonitorLocalVar(inst.line - 1, wroteOrFirstVisitVars, relevant)
                } else {
                    generateMonitorLocalVar(inst.line - 1, availableVars.values, relevant)
                }
                modifications.add(inst to insnList)
                if (changedLocalVarsOnly) {
                    wroteOrFirstVisitVars.clear()
                }
            }

            i++
        }

        println("Total modifications to be inserted: ${modifications.size}")  // 调试信息: 总的修改指令数
        for ((inst, insnList) in modifications) {
            println("Inserting modification at instruction: $inst")  // 调试信息: 插入指令的位置
            if (inst.next is FrameNode) {
                var insertBefore = inst.next
                while (insertBefore is FrameNode) {
                    insertBefore = insertBefore.next
                }
                methodNode.instructions.insertBefore(insertBefore, insnList)
            } else if (inst.next is TypeInsnNode && inst.next.opcode == NEW) {
                methodNode.instructions.insertBefore(inst, insnList)
            } else {
                methodNode.instructions.insert(inst, insnList)
            }
        }

        insertEnterMonitor(owner, methodNode)
        println("Finished transforming method: $fullMethodName")  // 调试信息: 方法处理完成
    }



    private fun insertEnterMonitor(owner: String, methodNode: MethodNode) {
        val methodName = "${owner.replace("/", ".")}::${methodNode.name}"
        val printNameInsnList = InsnList().apply {
            add(LdcInsnNode(methodName))
            add(
                MethodInsnNode(
                    INVOKESTATIC,
                    Type.getInternalName(DetectMonitor::class.java),
                    DetectMonitor::monitorEnterMethod.name,
                    "(Ljava/lang/String;)V"
                )
            )
        }
        methodNode.instructions.first?.apply {
            methodNode.instructions.insertBefore(this, printNameInsnList)
        } ?: methodNode.instructions.insert(printNameInsnList)
    }

    private fun generateMonitorLocalVar(
        line: Int,
        visitedVars: Collection<LocalVariableNode>,
        relevant: Boolean
    ): InsnList {
        val list = InsnList()

        // 1. Debug: Check visited vars
        println("Visited Vars: ${visitedVars.map { it.name }}")

        // Skip if no variables or only 'this'
        if (visitedVars.isEmpty() || visitedVars.all { it.name == "this" }) {
            println("No variables or only 'this' found. Skipping generation.")
            return list
        }

        // 2. Debug: Check line number
        println("Line number: $line")

        // Add instructions based on the line number
        when (line) {
            in -1..5 -> {
                list.add(InsnNode(ICONST_0 + line))
            }
            in Byte.MIN_VALUE..Byte.MAX_VALUE -> {
                list.add(IntInsnNode(BIPUSH, line))
            }
            in Short.MIN_VALUE..Short.MAX_VALUE -> {
                list.add(IntInsnNode(SIPUSH, line))
            }
            else -> list.add(IntInsnNode(LDC, line))
        }

        // 3. Debug: Creating HashMap
        println("Creating new HashMap")
        list.add(TypeInsnNode(NEW, "java/util/HashMap"))
        list.add(InsnNode(DUP))
        list.add(
            MethodInsnNode(
                INVOKESPECIAL, "java/util/HashMap",
                "<init>", "()V", false
            )
        )

        // 4. Process each local variable
        for (localVar in visitedVars) {
            if (localVar.name == "this") {
                println("Skipping 'this' variable.")
                continue
            }

            // 5. Debug: Print variable name and type
            println("Processing variable: ${localVar.name}, Type: ${localVar.desc}")

            list.add(InsnNode(DUP))
            list.add(LdcInsnNode(localVar.name))
            list.add(loadVar(localVar))

            // 6. Debug: Check loaded variable value
            val loadedValue = loadVar(localVar)
            println("Loading variable: ${localVar.name}, Value: $loadedValue")


            // 7. Debug: Check boxIfNeed
            val boxIfNeed = boxIfNeed(localVar.desc)
            if (boxIfNeed != null) {
                println("Boxed instruction added for: ${localVar.name}")
                list.add(boxIfNeed)
            }

            // Add to HashMap
            list.add(
                MethodInsnNode(
                    INVOKEVIRTUAL, "java/util/HashMap",
                    "put", "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;", false
                )
            )
            list.add(InsnNode(POP))

            // 8. Debug: After adding to HashMap
            println("Variable '${localVar.name}' added to HashMap with value: $loadedValue")
        }

        // 9. Debug: Add final relevant check
        if (relevant) {
            println("Adding relevant flag: true")
            list.add(InsnNode(ICONST_1))
        } else {
            println("Adding relevant flag: false")
            list.add(InsnNode(ICONST_0))
        }

        // 10. Debug: Add monitorLocalVar call
        println("Adding monitorLocalVar method call")
        list.add(
            MethodInsnNode(
                AdviceAdapter.INVOKESTATIC, Type.getInternalName(DetectMonitor::class.java),
                DetectMonitor::monitorLocalVar.name,
                "(ILjava/util/HashMap;Z)V", false
            )
        )

        return list
    }




    private fun analyzeControlFlow(methodNode: MethodNode, owner: String) {
        val labelToLine = mutableMapOf<LabelNode, Int>()
        var currentLine = -1
        var firstLine = -1
        println("Starting analyzeControlFlow for method: ${methodNode.name} in class: $owner")

        // Iterate through method instructions to map line numbers
        for (inst in methodNode.instructions) {
            if (inst is LineNumberNode) {
                currentLine = inst.line
                if (firstLine == -1) firstLine = currentLine
                println("LineNumberNode found: $currentLine")
            }
            if (inst is LabelNode && currentLine != -1) {
                labelToLine[inst] = currentLine
                println("LabelNode found at line $currentLine")
            }
        }
        val defaultLine = if (firstLine != -1) firstLine else 0
        println("Default line set to: $defaultLine")

        // Collect local variable names by index
        val localVars = methodNode.localVariables?.associateBy({ it.index }, { it.name }) ?: emptyMap()
        println("Local variables: $localVars")

        val modifications = mutableListOf<Pair<AbstractInsnNode, InsnList>>()
        var i = 0

        // Process instructions
        while (i < methodNode.instructions.size()) {
            val inst = methodNode.instructions[i]

            // If it's a jump instruction
            if (inst is JumpInsnNode && inst.opcode != GOTO) {
                println("Processing JumpInsnNode: ${inst.opcode}")

                // Helper function to find line number before the instruction
                fun findLineNumberBefore(insn: AbstractInsnNode, default: Int): Int {
                    var current: AbstractInsnNode? = insn
                    while (current != null) {
                        if (current is LineNumberNode) {
                            println("Found LineNumberNode before jump: ${current.line}")
                            return current.line
                        }
                        current = current.previous
                    }
                    return default
                }

                val lineNumber = findLineNumberBefore(inst, defaultLine)
                println("Line number for this jump: $lineNumber")

                // Extract left-hand expression
                var leftExpr = "unknown"
                var isField = false
                var prevInst = inst.previous
                while (prevInst != null) {
                    when (prevInst) {
                        is VarInsnNode -> if (prevInst.opcode in listOf(ALOAD, ILOAD, FLOAD, DLOAD, LLOAD)) {
                            leftExpr = localVars[prevInst.`var`] ?: "var${prevInst.`var`}"
                            break
                        }
                        is FieldInsnNode -> if (prevInst.opcode == GETFIELD) {
                            leftExpr = "this.${prevInst.name}"
                            isField = true
                            break
                        }
                        is MethodInsnNode -> if (prevInst.opcode == INVOKEVIRTUAL) {
                            leftExpr = "${prevInst.owner.replace('/', '.')}.${prevInst.name}()"
                            break
                        }
                    }
                    prevInst = prevInst.previous
                }
                println("Left-hand expression: $leftExpr")

                // Extract right-hand expression for comparison opcodes
                var rightExpr = "unknown"
                if (inst.opcode in listOf(IF_ICMPEQ, IF_ICMPNE, IF_ICMPLT, IF_ICMPGE, IF_ICMPGT, IF_ICMPLE)) {
                    var rightInst = inst.previous
                    while (rightInst != null) {
                        if (rightInst is FieldInsnNode && rightInst.opcode == GETFIELD) {
                            rightExpr = "this.${rightInst.name}"
                            break
                        } else if (rightInst is VarInsnNode && rightInst.opcode in listOf(ILOAD, ALOAD, FLOAD, DLOAD, LLOAD)) {
                            rightExpr = localVars[rightInst.`var`] ?: "var${rightInst.`var`}"
                            break
                        } else if (rightInst is MethodInsnNode && rightInst.opcode == INVOKEVIRTUAL) {
                            rightExpr = "${rightInst.owner.replace('/', '.')}.${rightInst.name}()"
                            break
                        }
                        rightInst = rightInst.previous
                    }
                }
                println("Right-hand expression: $rightExpr")

                // Create the condition based on the opcode
                val condition = when (inst.opcode) {
                    IFEQ -> if (isField) "$leftExpr != false" else "$leftExpr != 0"
                    IFNE -> if (isField) "$leftExpr == false" else "$leftExpr == 0"
                    IFLT -> "$leftExpr >= 0"
                    IFGE -> "$leftExpr < 0"
                    IFGT -> "$leftExpr <= 0"
                    IFLE -> "$leftExpr > 0"
                    IF_ICMPEQ -> "$leftExpr != $rightExpr"
                    IF_ICMPNE -> "$leftExpr == $rightExpr"
                    IF_ICMPLT -> "$leftExpr >= $rightExpr"
                    IF_ICMPGE -> "$leftExpr < $rightExpr"
                    IF_ICMPGT -> "$leftExpr <= $rightExpr"
                    IF_ICMPLE -> "$leftExpr > $rightExpr"
                    IFNONNULL -> "$leftExpr == null"
                    IFNULL -> "$leftExpr != null"
                    else -> "unknown_condition_${inst.opcode}"
                }
                println("Condition for jump: $condition")

                // Insert monitoring before the jump (for branch not taken)
                val monitorNotTakenInsnList = InsnList().apply {
                    add(LdcInsnNode(owner.replace("/", ".")))
                    add(LdcInsnNode(methodNode.name))
                    add(LdcInsnNode(lineNumber))
                    add(LdcInsnNode("if ($condition)"))
                    add(InsnNode(ICONST_0)) // executed = false
                    add(
                        MethodInsnNode(
                            INVOKESTATIC,
                            Type.getInternalName(DetectMonitor::class.java),
                            "monitorBranch",
                            "(Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;Z)V",
                            false
                        )
                    )
                }

                // Insert monitoring at the jump target (for branch taken)
                val monitorTakenInsnList = InsnList().apply {
                    add(LdcInsnNode(owner.replace("/", ".")))
                    add(LdcInsnNode(methodNode.name))
                    add(LdcInsnNode(lineNumber))
                    add(LdcInsnNode("if ($condition)"))
                    add(InsnNode(ICONST_1)) // executed = true
                    add(
                        MethodInsnNode(
                            INVOKESTATIC,
                            Type.getInternalName(DetectMonitor::class.java),
                            "monitorBranch",
                            "(Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;Z)V",
                            false
                        )
                    )
                }

                modifications.add(inst.label.next to monitorNotTakenInsnList)      // 跳转到了 L1 ⇒ true 分支
                modifications.add(inst.next to monitorTakenInsnList)

                println("Monitoring instructions inserted for jump at index $i")

            }

            if (inst is JumpInsnNode && inst.opcode == GOTO) {
                val targetLabel = inst.label
                val targetIndex = methodNode.instructions.indexOf(targetLabel)
                if (targetIndex < i) {
                    val lineNumber = labelToLine[targetLabel] ?: defaultLine
                    val loopDescription = "while at line $lineNumber"
                    val monitorLoopInsnList = InsnList().apply {
                        add(LdcInsnNode(owner.replace("/", ".")))
                        add(LdcInsnNode(methodNode.name))
                        add(LdcInsnNode(lineNumber))
                        add(LdcInsnNode(loopDescription))
                        add(
                            MethodInsnNode(
                                INVOKESTATIC,
                                Type.getInternalName(DetectMonitor::class.java),
                                "monitorLoop",
                                "(Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;)V",
                                false
                            )
                        )
                    }
                    modifications.add(inst to monitorLoopInsnList)
                    println("Monitoring instructions inserted for loop at index $i")
                }
            }
            i++
        }

        // Insert all modifications at the calculated positions
        for ((inst, insnList) in modifications) {
            methodNode.instructions.insertBefore(inst, insnList)
            println("Inserted modifications before instruction at index ${methodNode.instructions.indexOf(inst)}")
        }

        println("Finished analyzeControlFlow for method: ${methodNode.name}")
    }


    private fun analyzeMethodCalls(methodNode: MethodNode, owner: String) {
        val labelToLine = mutableMapOf<LabelNode, Int>()
        var currentLine = -1
        var firstLine = -1
        for (inst in methodNode.instructions) {
            if (inst is LineNumberNode) {
                currentLine = inst.line
                if (firstLine == -1) firstLine = currentLine
            }
            if (inst is LabelNode && currentLine != -1) {
                labelToLine[inst] = currentLine
            }
        }
        val defaultLine = if (firstLine != -1) firstLine else 0

        val modifications = mutableListOf<Pair<AbstractInsnNode, InsnList>>()
        var i = 0
        while (i < methodNode.instructions.size()) {
            val inst = methodNode.instructions[i]
            if (inst is MethodInsnNode && inst.opcode in listOf(INVOKESTATIC, INVOKEVIRTUAL, INVOKESPECIAL, INVOKEINTERFACE)) {
                val calledClass = inst.owner
                // Skip whitelisted classes
                if (calledClass in classNameWhiteList) {
                    i++
                    continue
                }
                // Skip java.lang.* <init> methods and self-calls (owner == calledClass && methodNode.name == inst.name)
                if ((calledClass.startsWith("java/lang") && inst.name == "<init>") ||
                    (calledClass == owner && inst.name == methodNode.name)) {
                    i++
                    continue
                }

                fun findLineNumberBefore(insn: AbstractInsnNode, default: Int): Int {
                    var current: AbstractInsnNode? = insn
                    while (current != null) {
                        if (current is LineNumberNode) return current.line
                        current = current.previous
                    }
                    return default
                }

                val lineNumber = findLineNumberBefore(inst, defaultLine)

                val monitorCallInsnList = InsnList().apply {
                    add(LdcInsnNode(owner.replace("/", ".")))
                    add(LdcInsnNode(methodNode.name))
                    add(LdcInsnNode(lineNumber))
                    add(LdcInsnNode(calledClass))
                    add(LdcInsnNode(inst.name))
                    add(
                        MethodInsnNode(
                            INVOKESTATIC,
                            Type.getInternalName(DetectMonitor::class.java),
                            "monitorMethodCall",
                            "(Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;Ljava/lang/String;)V",
                            false
                        )
                    )
                }
                modifications.add(inst to monitorCallInsnList)
            }
            i++
        }
        for ((inst, insnList) in modifications) {
            methodNode.instructions.insertBefore(inst, insnList)
        }
    }
}