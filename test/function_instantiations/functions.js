/*
Repo to test the 4 different ways of instantiating functions in Javascript

Goal: ensure the name of the function is identified by the inverse synth pipeline for
        each function instantiation
*/

// arrow functions
var add = (a,b) => a + b


var stringLowerUpper = (string) => {
    if(string.charAt(0) == 'a'){
        console.log('starts with a');
        return string.toUpperCase();
    }
    else {
        console.log('does not start with a');
        return string.toLowerCase(); 
    }
 }
 
// functions as a statement
function subtract(a, b) {
    let difference = a - b;
    return difference;
}

function getBook() {
    let book = {
        Id:1,
        Title:'Notes on an Execution',
        Price: 30,
        Available: true
    };
    return book.Available; 
};

// functions as an expression
// doesn't need to have a name, unlike statement functions 
// you can give the function a name, but the name of the function expression is local to the function body 

let multiply = function m(num1,num2) {
    let product = num1 * num2; 
    return product;
};
// to call the above function, you'd use var product = multiply(9, 10), not m(..,...)

let firstletter = function(string) {
    let first = string.charAt(0);
    return first;
}
// to call the above function, you'd use firstletter (the function within is anonymous)

// function as a constructor
function shoes(size, mark){
    this.size = size;
    this.mark = mark;
};


//  shorthand syntax
// similar to getter/setter (I'm struggling to find good examples of this structure online)
// const obj = {
//     items:[],
//     get(index){
//         return this.items[index];
//     }
// }

// items.add("foo", "bar");
// items.get(1) // => "bar"

module.exports = {
    add,
    subtract,
    multiply,
    stringLowerUpper,
    firstletter,
    shoes,
    getBook
  }
