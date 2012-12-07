import sublime, sublime_plugin
import re

COMMENT_CLOSE = '*/'
INDENTIFIER   = '[a-zA-Z_$][a-zA-Z_$0-9]*'

class DocjsParser:

    def parse( self, source ):
        snippet = self.parseFunctionDeclare( source );
        if snippet:
            return snippet

        snippet = self.parseVar( source );
        if snippet:
            return snippet

        snippet = self.parseIdentAssign( source );
        if snippet:
            return snippet

        snippet = self.parseIdentProp( source );
        if snippet:
            return snippet

        snippet = self.parseStrProp( source );
        if snippet:
            return snippet

        return '\n * $1\n */'

    def parseIdentProp( self, source ):
        regexp = r"\s*(" + INDENTIFIER + r")\s*:\s*([^;]+);?"
        match = re.match( regexp, source )
        print( match)
        if match:
            val = match.group( 2 )
            name = match.group( 1 )
            type = self.guessType( val )

            if type == 'function':
                return self.parseFunctionExpr( source, name )

            info = {
                'type': type,
                'name': name
            }
            
            return self.getAssignComment( info )

        return None

    def parseStrProp( self, source ):
        regexp = r"\s*\[?\s*['\"]([^'\"]+)['\"]\s*\]?\s*:\s*([^;]+)"
        match = re.match( regexp, source )
        
        if match:
            val = match.group( 2 )
            name = match.group( 1 )
            print(name)
            print(val)
            type = self.guessType( val )
            print(type)
            if type == 'function':
                return self.parseFunctionExpr( source, name )

            info = {
                'type': type,
                'name': name
            }
            
            return self.getAssignComment( info )

        return None

    def parseIdentAssign( self, source ):
        regexp = r"(\s*)(" + INDENTIFIER + r")\s*=\s*([^;]+);?"
        match = re.search( regexp, source )

        if match:
            val = match.group( 3 )
            name = match.group( 2 )
            head = match.group( 1 )
            type = self.guessType( val )
            info = {
                'name': name,
                'type': type
            }

            if type == 'function':
                return self.parseFunctionExpr( source, name )

            if len( head ) == 0 and type == 'Object':
                info[ 'namespace' ] = 1
            elif re.match( r"[A-Z_]+$", name ):
                    info[ 'const' ] = 1

            return self.getAssignComment( info )

    def parseStrAssign( self, source ):
        regexp = r"\[?\s*['\"]([^'\"]+)['\"]\s*\]\s*=\s*([^;]+);?"
        match = re.search( regexp, source )

        if match:
            val = match.group( 2 )
            name = match.group( 1 )
            type = self.guessType( val )
            info = {
                'name': name,
                'type': type
            }

            if type == 'function':
                return self.parseFunctionExpr( source, name )

            if re.match( r"[A-Z_]+$", name ):
                    info[ 'const' ] = 1

            return self.getAssignComment( info )

    def parseVar( self, source ):
        regexp = r"(\s*)var\s+(" + INDENTIFIER + r")\s*=\s*([^;]+);?"
        match = re.search( regexp, source )
        
        if match:
            val = match.group( 3 )
            name = match.group( 2 )
            head = match.group( 1 )
            type = self.guessType( val )
            info = {
                'name': name,
                'type': type
            }

            if type == 'function':
                return self.parseFunctionExpr( source, name )

            if len( head ) == 0 and type == 'Object':
                info[ 'namespace' ] = 1
            elif re.match( r"[A-Z_]+$", name ):
                info[ 'const' ] = 1

            return self.getAssignComment( info )

        return None

    def getAssignComment( self, info ):
        text = []
        text.append( '' )
        text.append( '${1:[%s description]}' % ( info[ 'name' ] ) )
        text.append( '' )

        if 'const' in info:
            text.append( '@const' )

        if 'namespace' in info:
            text.append( '@namespace' )
        else:
            text.append( '@type {${2:%s}}' % ( info[ 'type' ] ) )

        return '\n * '.join( text ) + '\n */'

    def guessType( self, source ):
        if re.match( "['\"]", source ):
            return "string"

        if source == 'true' or source == 'false':
            return 'boolean'

        if re.match( "[0-9]+", source ):
            return 'number'

        if re.match( "{", source ):
            return "Object"

        if re.match( r"\[", source ):
            return "Array"

        if re.match( "/[^/]", source ):
            return "RegExp"

        if re.match( "function", source ):
            return 'function'

        match = re.match(r"new\s+([^;\(]+)")
        if match:
            return match.group( 1 )

        return '[type]'

    def parseArgs( self, source ):
        args = re.split( r",\s*", source.strip() )
        return args

    def parseFunctionExpr( self, source, name ):
        regexp = r"function\s*\(([^\)]*)"

        match = re.search( regexp, source )
        if match:
            return self.getFunctionComment( {
                "type": "function",
                "name": name,
                "args": self.parseArgs( match.group( 1 ) )
            } )

        return None

    def parseFunctionDeclare( self, source ):
        declaration = r"^\s*function\s+(" + INDENTIFIER + r")\s*\(([^\)]*)\s*"
        match = re.match( declaration, source )
        functionInfo = None
        if match:
            return self.getFunctionComment( {
                "type": "function",
                "name": match.group( 1 ),
                "args": self.parseArgs( match.group( 2 ) )
            } )

        return None

    def getFunctionComment( self, info ):
        text = []
        name = info[ 'name' ]
        index = 1
        text.append( '' )
        text.append( '${%d:[%s description]}' % ( index, name ) )
        text.append( '' )
        returnTag = 1

        if re.match( "[A-Z]", name ):
            text.append( '@constructor' )
            returnTag = 0

        if re.match( "[_]", name ):
            text.append( '@private' )

        args = info[ 'args' ]
        index += 1
        if len( args ) > 0 and len( args[ 0 ] ) > 0:
            for arg in args:
                text.append( '@param {${%d:[type]}} %s ${%d:[%s description]}' % (index, arg, index + 1, arg) )
                index += 2

        if returnTag > 0:
            text.append( '@return {${%d:[type]}} ${%d:[return description]}' % ( index, index + 1 ) )
        
        return '\n * '.join( text ) + '\n */'

class DocjsCommand( sublime_plugin.TextCommand ):

    def run( self, edit ):
        view = self.view
        settings = view.settings()
        point = view.sel()[0].end() + 1

        lineRegion = view.line( point )
        lineString = view.substr( lineRegion )

        snippet = DocjsParser().parse( lineString )
        print( snippet )
        view.run_command( 'insert_snippet', { "contents": snippet } )

class DocjsAddCommentCommand( sublime_plugin.TextCommand ):

    def run( self, edit ):
        view = self.view
        view.run_command( 'move_to', { 'to': 'bol' } )
        view.run_command( 'insert', { "characters": "/**\n" } )
        view.run_command( 'move', { "by": "lines", "forward": False } )
        view.run_command( 'move_to', { 'to': 'eol' } )
        
        view.run_command( 'docjs' )

class DocjsTagAutocompleteCommand( sublime_plugin.TextCommand ):

    def run( self, edit ):
        view = self.view
        lineRegion = view.line( view.sel()[ 0 ].end())
        view.run_command( 'insert_snippet', { 'contents': '@' } )
        view.run_command( 'auto_complete' )

class DocjsDeindentCommand( sublime_plugin.TextCommand ):

    def run( self, edit ):
        view = self.view
        lineRegion = view.line( view.sel()[ 0 ].end())
        view.insert( 
            edit, 
            lineRegion.end(), 
            re.sub( "^(\\s*)\\s\\*/.*", "\n\\1", view.substr( lineRegion ) )
        )
