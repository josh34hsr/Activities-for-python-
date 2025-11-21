1.Set

students = {"Anna", "Mark", "John", "Anna"}   # duplicate "Anna" removed
print("Initial set:", students)

students.add("Grace")
print("After adding Grace:", students)

students.remove("Mark")
print("After removing Mark:", students)

print("Is John in the set?", "John" in students)

2.Tuples 

person = ("Jasper", 20, "BSCS")

print("Name:", person[0])
print("Age:", person[1])
print("Course:", person[2])

3. Linked List

class Node:
    def __init__(self, data):
        self.data = data
        self.next = None


class LinkedList:
    def __init__(self):
        self.head = None

    def append(self, data):
        new_node = Node(data)

        if not self.head:
            self.head = new_node
            return

        temp = self.head
        while temp.next:
            temp = temp.next

        temp.next = new_node

    def display(self):
        temp = self.head
        while temp:
            print(temp.data, end=" -> ")
            temp = temp.next
        print("None")


ll = LinkedList()
ll.append("A")
ll.append("B")
ll.append("C")

ll.display()

A -> B -> C -> None

4.Stack

class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        """Insert an element on top of the stack."""
        self.items.append(item)

    def pop(self):
        """Remove and return the top element of the stack."""
        if self.is_empty():
            raise IndexError("Pop from an empty stack")
        return self.items.pop()

    def peek(self):
        """Return the top element without removing it."""
        if self.is_empty():
            raise IndexError("Peek from an empty stack")
        return self.items[-1]

    def is_empty(self):
        """Check if the stack is empty."""
        return len(self.items) == 0

    def size(self):
        """Return the number of elements in the stack."""
        return len(self.items)


stack = Stack()
stack.push(10)
stack.push(20)
stack.push(30)

print("Top:", stack.peek())
print("Popped:", stack.pop())
print("Size:", stack.size())

5.Tree

class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


class BinaryTree:
    def __init__(self, root_value):
        self.root = Node(root_value)

    def insert_left(self, parent, value):
        """Attach a new left child to a parent node."""
        parent.left = Node(value)
        return parent.left

    def insert_right(self, parent, value):
        """Attach a new right child to a parent node."""
        parent.right = Node(value)
        return parent.right

    def inorder(self, node):
        """Inorder traversal (Left, Root, Right)."""
        if node:
            self.inorder(node.left)
            print(node.value, end=" ")
            self.inorder(node.right)

    def preorder(self, node):
        """Preorder traversal (Root, Left, Right)."""
        if node:
            print(node.value, end=" ")
            self.preorder(node.left)
            self.preorder(node.right)

    def postorder(self, node):
        """Postorder traversal (Left, Right, Root)."""
        if node:
            self.postorder(node.left)
            self.postorder(node.right)
            print(node.value, end=" ")

tree = BinaryTree(10)
left = tree.insert_left(tree.root, 5)
right = tree.insert_right(tree.root, 20)

tree.insert_left(left, 3)
tree.insert_right(left, 7)
tree.insert_left(right, 15)
tree.insert_right(right, 25)

print("Inorder: ", end="")
tree.inorder(tree.root)

print("\nPreorder: ", end="")
tree.preorder(tree.root)

print("\nPostorder:", end=" ")
tree.postorder(tree.root)
