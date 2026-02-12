# Prompt word definition
DEBUG_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version of each buggy function for the 
provided bug report. For each buggy function, provide a fixed version. Output only the fixed functions in a single 
code block, with each function preceded by a comment `// Fixed Method X` (where X is the method number). Do not 
include any other text or explanations. """

DEBUG_PROMPT = """### Buggy Java Functions (please generate fixed versions for each):
```java```
{BUGGY_CODE}

Debugging Information (e.g., Local Variables, Control Flow, Method Call):
- Local Variables: Shows values of variables at specific lines.
- Control Flow: Displays conditions and whether they were true/false.
- Method Call: Logs method invocations and call stack.
{DEBUG_INFO}

Function Call Context:
This section provides details of the methods being invoked in the current execution flow, including:
- Method Name: The name of the method being called.
- Comment: The comments or documentation describing the method's purpose and behavior.
- Source Code: The actual code of the method, or a note if the method body is not provided.
{CALL_INFO}

Please provide the fixed versions of all buggy functions in a single code block, with each fixed function preceded by 
a comment `// Fixed Method X` (where X is the method number starting from 1). """

EXAMPLE_INPUT_FUNC_DEBUG = """### Buggy Java Functions (please generate fixed versions for each):
```java```
// Method 1
public Vector3D intersection(final SubLine subLine, final boolean includeEndPoints) {
    // compute the intersection on infinite line
    Vector3D v1D = line.intersection(subLine.line);
    // check location of point with respect to first sub-line
    Location loc1 = remainingRegion.checkPoint(line.toSubSpace(v1D));
    // check location of point with respect to second sub-line
    Location loc2 = subLine.remainingRegion.checkPoint(subLine.line.toSubSpace(v1D));
    if (includeEndPoints) {
        return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v1D : null;
    } else {
        return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v1D : null;
    }
}

// Method 2
public Vector2D intersection(final SubLine subLine, final boolean includeEndPoints) {
    // retrieve the underlying lines
    Line line1 = (Line) getHyperplane();
    Line line2 = (Line) subLine.getHyperplane();
    // compute the intersection on infinite line
    Vector2D v2D = line1.intersection(line2);
    // check location of point with respect to first sub-line
    Location loc1 = getRemainingRegion().checkPoint(line1.toSubSpace(v2D));
    // check location of point with respect to second sub-line
    Location loc2 = subLine.getRemainingRegion().checkPoint(line2.toSubSpace(v2D));
    if (includeEndPoints) {
        return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v2D : null;
    } else {
        return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v2D : null;
    }
}

Debugging Information (e.g., Local Variables, Control Flow, Method Call):
- Local Variables: Shows values of variables at specific lines.
- Control Flow: Displays conditions and whether they were true/false.
- Method Call: Logs method invocations and call stack.

=== Debug Info for Test: org.apache.commons.math3.geometry.euclidean.threed.SubLineTest::testIntersectionNotIntersecting ===

org.apache.commons.math3.geometry.euclidean.threed.SubLine:intersection:112->[Local Variables] "{subLine=org.apache.commons.math3.geometry.euclidean.threed.SubLine@5e746d37, includeEndPoints=true}"
org.apache.commons.math3.geometry.euclidean.threed.SubLine:intersection:113->[Method Call] Call Stack: org.apache.commons.math3.geometry.euclidean.threed.SubLine.intersection:113 -> org.apache.commons.math3.geometry.euclidean.threed.Line.intersection
org.apache.commons.math3.geometry.euclidean.threed.SubLine:intersection:116->[Method Call] Call Stack: org.apache.commons.math3.geometry.euclidean.threed.SubLine.intersection:116 -> org.apache.commons.math3.geometry.euclidean.threed.Line.toSubSpace

=== Debug Info for Test: org.apache.commons.math3.geometry.euclidean.twod.SubLineTest::testIntersectionParallel ===

org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:112->[Local Variables] {"subLine":{"hyperplane":{},"remainingRegion":{}},"includeEndPoints":true}
org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:113->[Method Call] Call Stack: org.apache.commons.math3.geometry.euclidean.twod.SubLine.intersection:113 -> org.apache.commons.math3.geometry.euclidean.twod.SubLine.getHyperplane
org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:113->[Local Variables] {"line1":{"angle":1.5707963267948966,"cos":6.123233995736766E-17,"sin":1.0,"originOffset":0.0}}
org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:114->[Method Call] Call Stack: org.apache.commons.math3.geometry.euclidean.twod.SubLine.intersection:114 -> org.apache.commons.math3.geometry.euclidean.twod.SubLine.getHyperplane
org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:116->[Local Variables] {"line2":{"angle":1.5707963267948966,"cos":6.123233995736766E-17,"sin":1.0,"originOffset":-66.0}}
org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:117->[Method Call] Call Stack: org.apache.commons.math3.geometry.euclidean.twod.SubLine.intersection:117 -> org.apache.commons.math3.geometry.euclidean.twod.Line.intersection
org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:120->[Method Call] Call Stack: org.apache.commons.math3.geometry.euclidean.twod.SubLine.intersection:120 -> org.apache.commons.math3.geometry.euclidean.twod.SubLine.getRemainingRegion
org.apache.commons.math3.geometry.euclidean.twod.SubLine:intersection:120->[Method Call] Call Stack: org.apache.commons.math3.geometry.euclidean.twod.SubLine.intersection:120 -> org.apache.commons.math3.geometry.euclidean.twod.Line.toSubSpace

Function Call Context:
This section provides details of the methods being invoked in the current execution flow, including:
- Method Name: The name of the method being called.
- Comment: The comments or documentation describing the method's purpose and behavior.
- Source Code: The actual code of the method, or a note if the method body is not provided.

Method: org.apache.commons.math3.geometry.euclidean.threed.Line.intersection
Comment:
    /** Get the intersection point of the instance and another line.
     * @param line other line
     * @return intersection point of the instance and the other line
     * or null if there are no intersection points
     */
Source Code:
    public Vector3D intersection(final Line line) {
        final Vector3D closest = closestPoint(line);
        return line.contains(closest) ? closest : null;
    }

Method: org.apache.commons.math3.geometry.euclidean.threed.Line.toSubSpace
Comment:
    /** {@inheritDoc}
     * @see #getAbscissa(Vector3D)
     */
Source Code:
    public Vector1D toSubSpace(final Vector<Euclidean3D> point) {
        return new Vector1D(getAbscissa((Vector3D) point));
    }

Method: org.apache.commons.math3.geometry.euclidean.twod.Line.intersection
Comment:
    /** Get the intersection point of the instance and another line.
     * @param other other line
     * @return intersection point of the instance and the other line
     * or null if there are no intersection points
     */
Source Code:
    public Vector2D intersection(final Line other) {
        final double d = sin * other.cos - other.sin * cos;
        if (FastMath.abs(d) < 1.0e-10) {
            return null;
        }
        return new Vector2D((cos * other.originOffset - other.cos * originOffset) / d,
                            (sin * other.originOffset - other.sin * originOffset) / d);
    }

Method: org.apache.commons.math3.geometry.euclidean.twod.Line.toSubSpace
Comment:
    [No comment]
Source Code:
    [No method body]

Method: org.apache.commons.math3.geometry.euclidean.twod.SubLine.getHyperplane
Comment:
    [No comment]
Source Code:
    [No method body]

Method: org.apache.commons.math3.geometry.euclidean.twod.SubLine.getRemainingRegion
Comment:
    [No comment]
Source Code:
    [No method body]
"""

EXAMPLE_OUTPUT_FUNC_BASE = """
```java```
// Fixed Method 1
public Vector3D intersection(final SubLine subLine, final boolean includeEndPoints) {
 
         // compute the intersection on infinite line
         Vector3D v1D = line.intersection(subLine.line);
         if (v1D == null) {
             return null;
         }
 
         // check location of point with respect to first sub-line
         Location loc1 = remainingRegion.checkPoint(line.toSubSpace(v1D));

        // check location of point with respect to second sub-line
        Location loc2 = subLine.remainingRegion.checkPoint(subLine.line.toSubSpace(v1D));

        if (includeEndPoints) {
            return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v1D : null;
        } else {
            return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v1D : null;
        }

    }

// Fixed Method 2
public Vector2D intersection(final SubLine subLine, final boolean includeEndPoints) {

        // retrieve the underlying lines
        Line line1 = (Line) getHyperplane();
        Line line2 = (Line) subLine.getHyperplane();
 
         // compute the intersection on infinite line
         Vector2D v2D = line1.intersection(line2);
         if (v2D == null) {
             return null;
         }
 
         // check location of point with respect to first sub-line
         Location loc1 = getRemainingRegion().checkPoint(line1.toSubSpace(v2D));

        // check location of point with respect to second sub-line
        Location loc2 = subLine.getRemainingRegion().checkPoint(line2.toSubSpace(v2D));

        if (includeEndPoints) {
            return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v2D : null;
        } else {
            return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v2D : null;
        }

    }
"""
HISTORY_DEBUG_D4J = [
    {
        "role": "system",
        "content": DEBUG_INSTRUCTION
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_DEBUG
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_BASE
    }
]


PURE_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version for each buggy function. Do not 
response anything else except the refined version of buggy function. """


EXAMPLE_INPUT_FUNC_REFINE = """
```java```
// Method 1
public Vector3D intersection(final SubLine subLine, final boolean includeEndPoints) {
    // compute the intersection on infinite line
    Vector3D v1D = line.intersection(subLine.line);
    // check location of point with respect to first sub-line
    Location loc1 = remainingRegion.checkPoint(line.toSubSpace(v1D));
    // check location of point with respect to second sub-line
    Location loc2 = subLine.remainingRegion.checkPoint(subLine.line.toSubSpace(v1D));
    if (includeEndPoints) {
        return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v1D : null;
    } else {
        return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v1D : null;
    }
}

// Method 2
public Vector2D intersection(final SubLine subLine, final boolean includeEndPoints) {
    // retrieve the underlying lines
    Line line1 = (Line) getHyperplane();
    Line line2 = (Line) subLine.getHyperplane();
    // compute the intersection on infinite line
    Vector2D v2D = line1.intersection(line2);
    // check location of point with respect to first sub-line
    Location loc1 = getRemainingRegion().checkPoint(line1.toSubSpace(v2D));
    // check location of point with respect to second sub-line
    Location loc2 = subLine.getRemainingRegion().checkPoint(line2.toSubSpace(v2D));
    if (includeEndPoints) {
        return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v2D : null;
    } else {
        return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v2D : null;
    }
}

Please provide the fixed versions of all buggy functions in a single code block, with each fixed function preceded by a comment `// Fixed Method X` (where X is the method number starting from 1).
"""

HISTORY_PURE_D4J = [
        {
            "role": "system",
            "content": PURE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_FUNC_REFINE
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_FUNC_BASE
        },
]


USER_PROMPT = """
```java```
{BUGGY_CODE}

Please provide the fixed versions of all buggy functions in a single code block, with each fixed function preceded by a comment `// Fixed Method X` (where X is the method number starting from 1).
"""

# Exception mode instructions
EXCEPTION_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version for each buggy function 
based on the provided buggy code and exception information. Do not respond with anything else except the refined 
version of the buggy function. """

EXAMPLE_INPUT_FUNC_EXCEPTION = """
```java```
// Method 1
public Vector3D intersection(final SubLine subLine, final boolean includeEndPoints) {
    // compute the intersection on infinite line
    Vector3D v1D = line.intersection(subLine.line);
    // check location of point with respect to first sub-line
    Location loc1 = remainingRegion.checkPoint(line.toSubSpace(v1D));
    // check location of point with respect to second sub-line
    Location loc2 = subLine.remainingRegion.checkPoint(subLine.line.toSubSpace(v1D));
    if (includeEndPoints) {
        return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v1D : null;
    } else {
        return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v1D : null;
    }
}

// Method 2
public Vector2D intersection(final SubLine subLine, final boolean includeEndPoints) {
    // retrieve the underlying lines
    Line line1 = (Line) getHyperplane();
    Line line2 = (Line) subLine.getHyperplane();
    // compute the intersection on infinite line
    Vector2D v2D = line1.intersection(line2);
    // check location of point with respect to first sub-line
    Location loc1 = getRemainingRegion().checkPoint(line1.toSubSpace(v2D));
    // check location of point with respect to second sub-line
    Location loc2 = subLine.getRemainingRegion().checkPoint(line2.toSubSpace(v2D));
    if (includeEndPoints) {
        return ((loc1 != Location.OUTSIDE) && (loc2 != Location.OUTSIDE)) ? v2D : null;
    } else {
        return ((loc1 == Location.INSIDE) && (loc2 == Location.INSIDE)) ? v2D : null;
    }
}

    Exception Information:
    java.lang.NullPointerException
    
Please provide the fixed versions of all buggy functions in a single code block, with each fixed function preceded by a comment `// Fixed Method X` (where X is the method number starting from 1).
"""

# History template for exception mode
HISTORY_EXCEPTION_D4J = [
    {
        "role": "system",
        "content": EXCEPTION_INSTRUCTION
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_EXCEPTION
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_BASE
    },
]

# Prompt template for exception mode
EXCEPTION_PROMPT = """
```java```
{BUGGY_CODE}
Exception Information:
{EXCEPTION_INFO}

Please provide the fixed versions of all buggy functions in a single code block, with each fixed function preceded by a comment `// Fixed Method X` (where X is the method number starting from 1).
"""