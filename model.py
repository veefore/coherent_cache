import simpy
import random

class Cache:
    def __init__(self, size, read_time, write_time, env):
        self.size = size
        self.read_time = read_time
        self.write_time = write_time
        self.env = env

    def read(self, address):
        yield self.env.timeout(self.read_time)

    def write(self, address):
        yield self.env.timeout(self.write_time)


class Message:
    def __init__(self, msg_type, data):
        self.type = msg_type
        self.data = data
        self.handled = False
        # Message types are: 0 - invalidate, 1 - write, 2 - read


class Mailbox:
    def __init__(self, node_id, post_office, env):
        self.id = node_id
        self.post_office = post_office
        self.input_messages = []
        self.post_office.register_mailbox(self)
        self.env = env

    def empty(self):
        print('mailbox.empty(), id', self.id, 'time', self.env.now)
        return len(self.input_messages) == 0

    def get_message(self):
        print('mailbox.get_message')
        return self.input_messages.pop(0)

    def get_messages(self):
        print('mailbox.get_messages')
        messages = self.input_messages
        self.input_messages = []
        return messages

    def send_message(self, message):
        print('mailbox.send_message', message)
        yield self.env.timeout(1)
        self.post_office.leave_message(self.id, message)

    def leave_message(self, message):
        print('mailbox.leave_message', message)
        self.input_messages.append(message)
            

class Processor:
    def __init__(self, mailbox, cache, directory, env):
        self.mailbox = mailbox
        self.cache = cache
        self.directory = directory
        self.write_address = None
        self.instructions = 0
        self.env = env

    def proc(self, chance):
        return True if random.randint(0, 100) < (chance * 100) else False

    def run(self):
        while True:
            yield self.env.timeout(1)
            print('Performing instruction, time', self.env.now)
            if self.proc(0.1): # Mem access chance
                # Decide on which operation it is
                readOp = self.proc(0.5)
                address = random.randint(0, self.cache.size - 1)
                print('It proced!', readOp, address)
                yield self.env.process(self.handle_mem_access(readOp, address))
            self.instructions = self.instructions + 1

    def handle_message(self, message):
        print('Handling message', message)
        if message.type == 0: # Invalidate type
            yield self.env.timeout(1)
            self.directory[message.data] = 0
        elif message.type == 1:
            yield self.env.timeout(1)
            self.directory[self.write_address] = 1
            yield self.env.timeout(1)
            self.cache.write(self.write_address)
            self.write_address = None

    def handle_messages(self, messages=None):
        print('Handling messages', messages)
        if messages is None:
            messages = self.mailbox.get_messages()
        for msg in messages:
            yield self.env.process(self.handle_message(msg))

    def handle_mem_access(self, readOp, address):
        print('handling mem access, time', self.env.now)
        if readOp:
            yield self.env.process(self.handle_messages())
            yield self.env.timeout(1)
            if self.directory[address] == 1:
                yield self.env.process(self.cache.read(address))
            else:
                yield self.env.process(self.mailbox.send_message(Message(2, address)))
                self.write_address = address
                while self.directory[address] == 0:
                    yield self.env.timeout(1)
                    if not self.mailbox.empty():
                        yield self.env.process(self.handle_message(self.mailbox.get_message()))
        else:
            messages = self.mailbox.get_messages()
            yield self.env.process(self.mailbox.send_message(Message(0, address)))
            yield self.env.process(self.mailbox.send_message(Message(1, 123))) # 123 as write data
            yield self.env.process(self.handle_messages(messages))
            yield self.env.timeout(1)
            yield self.env.process(self.cache.write(address))
            self.directory[address] = 1


class PostOffice:
    def __init__(self, pnodes, env):
        self.mailboxes = [None for x in range(pnodes)] # Dict: Id -> Mailbox obj
        self.input_messages = [[] for x in range(pnodes)] # Dict: Id -> list of messages from correspondent mailbox
        self.queue = [] # All messages put together in chronological order; entry type = tuple(id, msg)
        self.env = env

    def register_mailbox(self, mailbox):
        self.mailboxes[mailbox.id] = mailbox

    def leave_message(self, mailbox_id, message):
        print('postoffice.leave_message, id', mailbox_id)
        self.input_messages[mailbox_id].append(message)
        self.queue.append((mailbox_id, message))

    def empty(self):
        print('postoffice.empty')
        if len(self.queue) == 0:
            return True
        mailbox_id, msg = self.queue[0]
        while msg.handled == True:
            self.queue.pop(0)
            if len(self.queue) > 0:
                mailbox_id, msg = self.queue[0]
            else:
                return True
        return False

    def get_front_message(self):
        print('postoffice.get_front_message')
        yield self.env.timeout(1)
        mailbox_id, msg = self.queue.pop(0)
        self.input_messages[mailbox_id].pop(0)
        print('postoffice.get_front_message results:', mailbox_id, msg)
        return mailbox_id, msg

    def get_message(self, mailbox_id):
        print('postoffice.get_message, id', mailbox_id)
        yield self.env.timeout(1)
        return mailbox_id, self.input_messages[mailbox_id].pop(0)

    def send_messages(self, recipients, msg):
        print('postoffice.send_messages', recipients)
        yield self.env.timeout(1)
        for mailbox_id in recipients:
            print('mailbox_id', mailbox_id)
            self.mailboxes[mailbox_id].leave_message(msg)

    def send_message(self, recipient, msg):
        print('postoffice.send_message', recipient)
        yield self.env.timeout(1)
        self.mailboxes[recipient].leave_message(msg)


class DirectoryProcessor:
    def __init__(self, post_office, cache, directory, env):
        self.post_office = post_office
        self.cache = cache
        self.directory = directory
        self.write_address = None
        self.write_id = None # Used in handling write messages
        self.env = env


    def handle_invalidate(self, node_id, msg):
        print('dnode.handle_invalidate, id', node_id)
        addr = msg.data
        yield self.env.timeout(1)
        cached = self.directory[addr]
        try:
            cached.remove(node_id)
        except ValueError:
            pass
        yield self.env.process(self.post_office.send_messages(cached, msg))
        yield self.env.timeout(1)
        print('handle invalidate node id', node_id)
        self.directory[addr] = [node_id]
        self.write_address = addr
        self.write_id = node_id

    def handle_write(self, node_id, msg):
        print('dnode.handle_write, id', node_id)
        yield self.env.timeout(1)
        yield self.env.process(self.cache.write(self.write_address))
        self.write_address = None
        self.write_id = None

    def handle_read(self, node_id, msg):
        print('dnode.handle_read, id', node_id)
        addr = msg.data
        yield self.env.timeout(1)
        yield self.env.process(self.cache.read(addr))
        yield self.env.process(self.post_office.send_message(node_id, Message(1, 123)))
        yield self.env.timeout(1)
        self.directory[addr].append(node_id)

    def run(self):
        while True:
            print('starting dnode instruction, time', self.env.now)
            yield self.env.timeout(1)
            if not self.post_office.empty():
                print('dnode: post_office not empty', self.env.now)
                # Ensure, that if the last handled request was invalidate,
                # we handle the upcoming write correctly by making sure we handle it next.
                # By doing this we also make sure that there is no read request from other node
                # handled with invalid data.
                if self.write_address is not None:
                    node_id, msg = yield self.env.process(self.post_office.get_message(self.write_id))
                    print('write address not none, node_id', node_id)
                else:
                    node_id, msg = yield self.env.process(self.post_office.get_front_message())
                    print('write address none, node_id', node_id)
                print('dnode msg type', msg.type)
                yield self.env.timeout(1)
                if msg.type == 0:
                    yield self.env.process(self.handle_invalidate(node_id, msg))
                elif msg.type == 1:
                    yield self.env.process(self.handle_write(node_id, msg))
                elif msg.type == 2:
                    yield self.env.process(self.handle_read(node_id, msg))
                msg.handled = True


class DirectoryNode:
    def __init__(self, pnodes, cache_size, read_time, write_time, env):
        self.post_office = PostOffice(pnodes, env)
        self.cache = Cache(cache_size, read_time, write_time, env)
        self.directory = [[] for x in range(cache_size)]
        self.processor = DirectoryProcessor(self.post_office, self.cache, self.directory, env)
        self.action = env.process(self.processor.run())


class ProcessingNode:
    def __init__(self, node_id, directory_node, cache_size, read_time, write_time, env):
        self.id = node_id
        self.mailbox = Mailbox(self.id, directory_node.post_office, env)
        self.cache = Cache(cache_size, read_time, write_time, env)
        self.directory = [0 for x in range(cache_size)]
        self.processor = Processor(self.mailbox, self.cache, self.directory, env)
        self.action = env.process(self.processor.run())

    def instructions_done(self):
        return self.processor.instructions


if __name__ == '__main__':
    env = simpy.Environment()
    random.seed()
    pnodes_cnt = 15
    cache_size = 500
    read_time = 5
    write_time = 10
    dnode = DirectoryNode(pnodes_cnt, cache_size, read_time, write_time, env)
    instructions_cnt = [0 for x in range (pnodes_cnt)]
    pnodes = [ProcessingNode(pnode_id, dnode, cache_size, read_time, write_time, env) for pnode_id in range(pnodes_cnt)]
    env.run(until=10000)
    total_instructions = 0
    for pnode in pnodes:
        total_instructions = total_instructions + pnode.instructions_done()
    print('total instructions', total_instructions)
    print('instruction per processing node', total_instructions / pnodes_cnt)
