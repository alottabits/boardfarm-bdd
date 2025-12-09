# Page structure vs Behavior Centric

The architecture proposed in the research report is based on **Model-Based Testing (MBT)**, which uses a **Finite State Machine (FSM)** structure. This FSM structure is specifically designed to achieve two core goals critical for highly volatile UIs:

1. **Algorithmic Test Path Generation:** Generating exhaustive, non-redundant test scenarios (a primary feature of tools like GraphWalker 1).  
2. **Total Decoupling and Resilience:** Insulating the test script from *which specific element* was clicked and *which specific page* was loaded, focusing only on the *resulting state*.

Here is a detailed breakdown of how the MBT/FSM graph structure works, and how it differs from the structural model:

---

## **1\. The Core Difference: State vs. Structure**

| Feature | Structural Model (DOM-centric) | MBT/FSM Model (Behavior-centric) |
| :---- | :---- | :---- |
| **Node Definition** | A physical **Page** (e.g., /login.html) or a specific **Element** (e.g., Submit Button). | A **Verifiable State** (or "Vertex"). This is the specific condition the UI is in after an action.1 |
| **Edge Definition** | A structural connection, like \[ :ON\_PAGE \] or \`\`. | An **Action/Transition** ("Edge"). This is the executable operation that moves the system from one verifiable state to another.1 |
| **Primary Goal** | Organize element locators for maintainability (POM). | Define the system's **behavior** and **flow** for automated test generation and verification.2 |

## **2\. The MBT/FSM Node (The Verifiable State)**

In the MBT approach, a Node represents a moment in time where the test system must stop, verify, and assert that the application is in the **expected condition**.

A State Node stores the following crucial information:

* **State Identity (Fingerprint):** Stable attributes that define the page or component, such as the URL pattern, the presence of key components, and a hash of the significant structural elements. This is how the system confirms it has landed in the *correct* state, even if the elements within that state have changed.  
* **Verification Logic:** The assertions required for that state (e.g., "The error message Username Required is visible," or "The Dashboard component is rendered"). A vertex in this model represents this verification point.1  
* **Element Descriptors:** This is where the structural information from your model is integrated. The Node stores a repository of resilient locators (getByRole(), getByTestId(), etc.) for every actionable element **present in that state**.

### **Example: The Login Page**

A "Login Page" might be represented by three distinct State Nodes:

| Node ID | State Description | Key Verification |
| :---- | :---- | :---- |
| V\_LOGIN\_FORM\_EMPTY | The standard login page, ready for input. | Verify: Login button is enabled, no error messages visible. |
| V\_LOGIN\_FORM\_ERROR | Login page after submitting empty fields. | Verify: Error banner is visible, fields are still present. |
| V\_DASHBOARD\_LOADED | The page that appears *after* successful login. | Verify: User name displayed, expected menu items are present. |

## 

## **3\. The MBT/FSM Edge (The Action/Transition)**

The Edge is the bridge between two States, and its purpose is purely to define the *action* that must be executed.

An Edge stores the following:

* **Action Logic:** The function that must be executed (e.g., type\_username\_and\_click\_submit).  
* **Locator Reference:** A pointer to the specific element descriptor (containing the resilient locators) stored in the **Source Node**.

### **Example: The Transition Edge**

| Edge ID | Source Node | Target Node | Action Logic |
| :---- | :---- | :---- | :---- |
| E\_SUBMIT\_VALID\_CREDS | V\_LOGIN\_FORM\_EMPTY | V\_DASHBOARD\_LOADED | Fill fields and click the element responsible for submission. |

### 

### **The Resilience Advantage**

This separation creates the necessary resilience:

1. **Test Script Stability:** The automated test script never calls the locator directly; it only calls the Edge ID: execute\_transition('E\_SUBMIT\_VALID\_CREDS'). This ID never changes.  
2. **Locator Volatility Isolation:** If the 'Submit Button' element changes its ID, Playwright's self-healing layer detects the change, finds the new resilient locator, and *updates the element descriptor stored in the source node* (V\_LOGIN\_FORM\_EMPTY).  
3. **Zero Test Script Change:** The test script remains identical because the Edge ID it calls is unchanged. The graph manages the volatility, insulating the execution logic completely.

This architecture, using the graph to define verifiable states (nodes) and executable transitions (edges) 1, is the backbone of Model-Based Testing and is why it provides a highly stable, maintainable interface for automation scripts, even in the face of continuous UI changes.

